"""
LLM judge fallback.

When GraphRAG cannot match a claim against the knowledge base (verdict "Undetermined"),
this module can ask an LLM to make the call instead. It is opt-in: it only runs when
TRUMORGPT_OFFLINE is not "1" and a backend is reachable. If no backend responds, it returns
None and the pipeline keeps the safe "Undetermined" verdict.

Backends tried in order: local Ollama (recommended, unlimited/private), Google Gemini,
OpenAI. Set the relevant env vars (OLLAMA_URL / GEMINI_API_KEY / OPENAI_API_KEY).
"""

import os
import re
import socket

import requests

PROMPT = (
    "You are a careful public-health fact-checker. Classify the claim as TRUE, FALSE, or "
    "UNDETERMINED. Use UNDETERMINED only when it genuinely cannot be verified from reliable "
    "health knowledge. Answer exactly in two lines:\n"
    "VERDICT: <True|False|Undetermined>\n"
    "REASON: <one short sentence>\n"
    "Claim: {claim}"
)


class LLMJudge:
    def __init__(self, ollama_url=None, ollama_model="llama3.1:8b",
                 gemini_model="gemini-3.8-flash"):
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = ollama_model
        self.gemini_model = gemini_model
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    # -- backend reachability ------------------------------------------------
    def _ollama_up(self):
        host = self.ollama_url.split("//")[-1].split(":")[0]
        port = int(self.ollama_url.rsplit(":", 1)[-1].split("/")[0])
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False

    def available(self):
        return self._ollama_up() or bool(self.gemini_key) or bool(self.openai_key)

    # -- backends ------------------------------------------------------------
    def _ollama(self, claim):
        payload = {"model": self.ollama_model, "prompt": PROMPT.format(claim=claim),
                   "stream": False, "options": {"temperature": 0.1}}
        r = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=60)
        if r.status_code == 200:
            return r.json().get("response", "")
        return None

    def _gemini(self, claim):
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.gemini_model}:generateContent?key={self.gemini_key}")
        payload = {"contents": [{"parts": [{"text": PROMPT.format(claim=claim)}]}],
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                                        "thinkingConfig": {"thinkingBudget": 0}}}
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            parts = r.json()["candidates"][0]["content"].get("parts", [])
            return parts[0].get("text", "") if parts else ""
        return None

    def _openai(self, claim):
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini",
                   "messages": [{"role": "user", "content": PROMPT.format(claim=claim)}],
                   "temperature": 0.1}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return None

    # -- public --------------------------------------------------------------
    def judge(self, claim):
        """Returns {verdict, reason, source} or None if no backend could answer."""
        text, source = None, None
        try:
            if self._ollama_up():
                text, source = self._ollama(claim), "Ollama"
            if text is None and self.gemini_key:
                text, source = self._gemini(claim), "Gemini"
            if text is None and self.openai_key:
                text, source = self._openai(claim), "OpenAI"
        except Exception:
            return None
        if not text:
            return None
        return self._parse(text, source)

    @staticmethod
    def _parse(text, source):
        m = re.search(r"VERDICT:\s*(true|false|undetermined)", text, re.I)
        if m:
            raw = m.group(1).lower()
            verdict = {"true": "True", "false": "False", "undetermined": "Undetermined"}[raw]
        else:
            up = text.upper()
            verdict = "True" if "TRUE" in up else ("False" if "FALSE" in up else "Undetermined")
        rm = re.search(r"REASON:\s*(.+)", text, re.I)
        reason = rm.group(1).strip().splitlines()[0] if rm else ""
        return {"verdict": verdict, "reason": reason, "source": f"LLM judge ({source})"}
