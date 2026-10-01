"""
Tests for the evaluation harness and robustness edge cases.

Covers:
- stable fused embedding dimension (BERT 384 + LDA 5 = 389, or fallback resized to 384)
- metric computation on a tiny hand-checked fixture
- pipeline robustness: empty claim, very long claim, non-English text,
  and a claim with no knowledge-base match must return Undetermined (not crash)
"""

import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
for p in (SRC, BASE):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("TRUMORGPT_OFFLINE", "1")

from scripts.evaluate import compute_metrics
from trumorgpt.lda_centrality import TopicEnhancedSentenceCentrality
from trumorgpt.pipeline import TrumorGPTPipeline


def test_embedding_dim_stable():
    engine = TopicEnhancedSentenceCentrality(eta=0.7, n_topics=5)
    engine.train_lda([
        "mRNA vaccines reduce severe COVID-19 hospitalizations.",
        "Healthy diet helps manage diabetes.",
    ])
    _, v = engine.compute_similarity_matrix(["Vaccines protect against viral infection."])
    assert v.shape[0] == 1
    assert v.shape[1] == engine.embedding_dim + 5


def test_metrics_fixture():
    golds = ["True", "True", "False", "False"]
    preds = ["True", "False", "False", "Undetermined"]
    m = compute_metrics(golds, preds)
    assert m["n"] == 4
    # 2 strict hits out of 4
    assert abs(m["strict"]["accuracy"] - 0.5) < 1e-9
    # 3 determined predictions, 2 of them correct
    assert m["determined"]["n"] == 3
    assert abs(m["determined"]["accuracy"] - (2 / 3)) < 1e-3
    assert m["undetermined_rate"] == 0.25


def test_pipeline_edge_cases():
    pipeline = TrumorGPTPipeline(data_dir=os.path.join(BASE, "data"))
    pipeline.initialize()

    for claim in [
        "",                                  # empty
        "covid " * 400,                      # very long
        "Le vaccin contre la COVID-19 est sur et efficace.",  # non-English
        "The 2024 budget deficit widened amid rising interest rates.",  # no KB match
    ]:
        res = pipeline.fact_check(claim)
        assert res["verdict"] in ("True", "False", "Undetermined")
        assert "metrics" in res and "explanation" in res

    # A claim with no knowledge-base overlap must abstain, not guess.
    res = pipeline.fact_check("The 2024 budget deficit widened amid rising interest rates.")
    assert res["verdict"] == "Undetermined"


def test_llm_judge_parse():
    """Parses LLM judge responses without any network access."""
    from trumorgpt.llm_judge import LLMJudge
    out = LLMJudge._parse("VERDICT: False\nREASON: contradicts verified evidence.", "Gemini")
    assert out["verdict"] == "False"
    assert out["source"].startswith("LLM judge")
    assert out["reason"].startswith("contradicts")
    assert LLMJudge._parse("The claim is TRUE", "Ollama")["verdict"] == "True"
    assert LLMJudge._parse("VERDICT: Undetermined\nREASON: unknown", "Ollama")["verdict"] == "Undetermined"
