"""
Live evidence retrieval for freshness.

The paper's knowledge graph is static and limited, which is one of its main drawbacks.
This module fetches current evidence for a claim from Wikipedia (keyless, no quota) so the
LLM judge reasons over up-to-date sources instead of only the sealed knowledge base.

Returns a small list of {title, url, snippet} dicts. Failures return an empty list; the
pipeline then falls back to the knowledge base and the judge's own knowledge.
"""

import re

import requests

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
UA = {"User-Agent": "TrumorGPT/1.0 (capstone fact-checker)"}

# Words that carry no search value on their own.
STOP = {
    "the", "a", "an", "is", "are", "was", "were", "does", "do", "did", "can", "could",
    "will", "would", "not", "no", "and", "or", "of", "to", "for", "in", "on", "it", "that",
    "this", "these", "those", "has", "have", "had", "be", "been", "being", "with", "about",
}


def _search_query(claim: str) -> str:
    words = re.findall(r"[A-Za-z0-9\-]+", claim)
    keep = [w for w in words if w.lower() not in STOP]
    return " ".join(keep[:12]) or claim[:120]


def fetch_evidence(claim: str, max_sources: int = 2, timeout: int = 12):
    """Return up to max_sources Wikipedia evidence snippets for a claim."""
    out = []
    try:
        r = requests.get(
            WIKI_API,
            params={"action": "query", "list": "search", "srsearch": _search_query(claim),
                    "format": "json", "srlimit": max_sources},
            headers=UA, timeout=timeout,
        )
        if r.status_code != 200:
            return out
        for item in r.json().get("query", {}).get("search", [])[:max_sources]:
            title = item["title"]
            s = requests.get(WIKI_SUMMARY.format(title=title.replace(" ", "_")),
                             headers=UA, timeout=timeout)
            if s.status_code != 200:
                continue
            d = s.json()
            out.append({
                "title": d.get("title", title),
                "url": d.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "snippet": (d.get("extract") or "")[:400],
            })
    except Exception:
        return out
    return out
