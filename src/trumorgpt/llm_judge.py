"""
LLM judge + freshness.

The paper's two big drawbacks are (1) a static, limited knowledge graph and (2) LLM
hallucination. This module addresses both: it asks a language model to judge a claim,
optionally grounded in freshly retrieved evidence (see web_retrieval), and it prefers a
local model so the demo runs without network or quota.

Backend order: local Ollama (default), then Gemini, then OpenAI, then a keyless public
endpoint. If no backend answers, it returns None and the pipeline keeps "Undetermined".
"""

import os
import re
import socket

import requests

SYSTEM = (
    "You are a careful medical fact-checker. Decide whether the claim is TRUE or FALSE. "
    "Use the retrieved evidence when it is relevant, and your medical knowledge otherwise. "
    "Answer exactly in two lines:\n"
    "VERDICT: <True|False>\n"
    "REASON: <one short sentence>"
)
POLLINATIONS_URL = "https://text.pollinations.ai/openai"


def build_prompt(claim: str, evidence=None) -> str:
    parts = [SYSTEM]
    if evidence:
        parts.append("Retrieved evidence:")
        for e in evidence[:2]:
            parts.append(f"- {e.get('title', '')}: {(e.get('snippet') or '')[:200]}")
    parts.append("Claim: " + claim)
    return "\n".join(parts)


class LLMJudge:
    def __init__(self, ollama_url=None, ollama_model=None,
                 gemini_model="gemini-3.8-flash"):
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")
        self.gemini_model = gemini_model
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.use_pollinations = os.getenv("TRUMORGPT_DISABLE_POLLINATIONS") != "1"
        self._active_model = None

    # -- reachability --------------------------------------------------------
    def _ollama_up(self):
        host = self.ollama_url.split("//")[-1].split(":")[0]
        port = int(self.ollama_url.rsplit(":", 1)[-1].split("/")[0])
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return True
        except OSError:
            return False

    def _pick_model(self):
        if self._active_model:
            return self._active_model
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            tags = [m["name"] for m in r.json().get("models", [])]
        except Exception:
            tags = []
        if self.ollama_model in tags:
            self._active_model = self.ollama_model
        elif tags:
            self._active_model = tags[0]
        else:
            self._active_model = self.ollama_model
        return self._active_model

    def available(self):
        return self._ollama_up() or bool(self.gemini_key) or bool(self.openai_key) or self.use_pollinations

    # -- backends ------------------------------------------------------------
    def _ollama(self, prompt):
        payload = {"model": self._pick_model(), "prompt": prompt, "stream": False,
                   "keep_alive": "30m",
                   "options": {"temperature": 0.1, "num_predict": 96}}
        r = requests.post(f"{self.ollama_url}/api/generate", json=payload, timeout=120)
        if r.status_code == 200:
            return r.json().get("response", "")
        return None

    def _gemini(self, prompt):
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.gemini_model}:generateContent?key={self.gemini_key}")
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                                        "thinkingConfig": {"thinkingBudget": 0}}}
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            parts = r.json()["candidates"][0]["content"].get("parts", [])
            return parts[0].get("text", "") if parts else ""
        return None

    def _openai(self, prompt):
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        payload = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}],
                   "temperature": 0.1}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers=headers, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return None

    def _pollinations(self, prompt):
        r = requests.get("https://text.pollinations.ai/" + requests.utils.quote(prompt)
                         + "?model=openai", timeout=60)
        if r.status_code == 200:
            return r.text
        return None

    # -- public --------------------------------------------------------------
    def judge(self, claim, evidence=None):
        """Returns {verdict, reason, source} or None if no backend could answer."""
        prompt = build_prompt(claim, evidence)
        text, source = None, None
        try:
            if self._ollama_up():
                text, source = self._ollama(prompt), f"Ollama ({self._pick_model()})"
            if text is None and self.gemini_key:
                text, source = self._gemini(prompt), "Gemini"
            if text is None and self.openai_key:
                text, source = self._openai(prompt), "OpenAI"
            if text is None and self.use_pollinations:
                text, source = self._pollinations(prompt), "Pollinations"
        except Exception:
            return None
        if not text:
            return None
        return self._parse(text, source)

    @staticmethod
    def _parse(text, source):
        m = re.search(r"VERDICT:\s*(true|false|undetermined)", text, re.I)
        if m:
            verdict = {"true": "True", "false": "False",
                       "undetermined": "Undetermined"}[m.group(1).lower()]
        else:
            up = text.upper()
            verdict = "True" if "TRUE" in up else ("False" if "FALSE" in up else "Undetermined")
        rm = re.search(r"REASON:\s*(.+)", text, re.I)
        reason = rm.group(1).strip().splitlines()[0] if rm else ""
        return {"verdict": verdict, "reason": reason, "source": f"LLM judge ({source})"}
