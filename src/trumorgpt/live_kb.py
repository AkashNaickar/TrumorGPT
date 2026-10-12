"""
On-demand reference knowledge graph (Option B), fast path.

The paper matches a claim against a large pre-built DBpedia health base. Instead of ingesting
that dump, this builds a small reference graph for the claim at query time from live evidence.
The build is heuristic (no extra LLM call) so the whole judgment needs only one model call.

    claim -> live evidence (Wikipedia) -> reference graph (claim entities linked to the
    evidence topic) -> entity-overlap match -> verdict from the LLM judge
"""

import re

from trumorgpt.web_retrieval import fetch_evidence

STOP = {
    "the", "a", "an", "is", "are", "was", "were", "does", "do", "did", "can", "could",
    "will", "would", "not", "no", "and", "or", "of", "to", "for", "in", "on", "it", "that",
    "this", "these", "those", "has", "have", "had", "be", "been", "being", "with", "about",
    "good", "bad", "safe", "health", "healthy", "some", "more", "less", "very", "than",
}


def claim_entities(claim: str):
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", claim)
    cand = [w for w in words if w[:1].isupper()] + [w for w in words if len(w) > 3]
    out = []
    for w in cand:
        if w.lower() in STOP:
            continue
        if all(w.lower() != o.lower() for o in out):
            out.append(w)
    return out[:6]


def build_live_reference_graph(claim, kg_builder=None, evidence=None, max_triples=8):
    """Build a reference graph for the claim from live evidence, without an LLM call."""
    if evidence is None:
        evidence = fetch_evidence(claim, max_sources=1)
    if not evidence:
        return None
    topic = evidence[0].get("title") or "Live evidence"
    text = " ".join((e.get("snippet") or "") for e in evidence).lower()

    triples = []
    for ent in claim_entities(claim):
        if ent.lower() in text:
            triples.append({"head": ent, "relation": "described_in", "tail": topic})
    if not triples:
        ents = claim_entities(claim)
        if ents:
            triples.append({"head": ents[0], "relation": "related_to", "tail": topic})
    if not triples:
        return None

    return {
        "graph_id": "live_evidence",
        "source": "Live retrieval",
        "topic": topic,
        "url": evidence[0].get("url", ""),
        "triples": triples[:max_triples],
    }


def _entities(kg):
    out = set()
    for t in (kg or {}).get("triples", []):
        for key in ("head", "tail"):
            v = str(t.get(key, "")).strip().lower()
            if v:
                out.add(v)
    return out


def entity_overlap(query_kg, ref_kg):
    """Fraction of the claim's entities that also appear in the reference graph."""
    q = _entities(query_kg)
    r = _entities(ref_kg)
    if not q or not r:
        return 0.0
    hits = 0
    for a in q:
        if any(a in b or b in a for b in r):
            hits += 1
    return hits / len(q)
