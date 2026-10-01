"""
Automated Test Suite for TrumorGPT Backend Prototype
Verifies all paper modules, mathematical proofs, and pipeline integration.
"""

import os
import sys

import numpy as np

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from trumorgpt.graph_builder import KnowledgeGraphBuilder
from trumorgpt.graph_rag import GraphRAGEngine
from trumorgpt.lda_centrality import TopicEnhancedSentenceCentrality
from trumorgpt.pipeline import TrumorGPTPipeline
from trumorgpt.tst_ranker import TopicSpecificTextRank


def test_lda_sentence_centrality():
    """Verifies LDA + BERT vector fusion shape and normalization (Section 3.2.1)."""
    engine = TopicEnhancedSentenceCentrality(eta=0.7, n_topics=5)
    sample_corpus = [
        "mRNA vaccines reduce severe COVID-19 hospitalizations.",
        "FDA approves booster shots for public health safety.",
        "Healthy diet and low sugar intake help manage diabetes."
    ]
    engine.train_lda(sample_corpus)

    sentences = ["Vaccines provide strong protection against viral infection."]
    W_s, v_matrix = engine.compute_similarity_matrix(sentences)

    assert v_matrix.shape[0] == 1
    assert v_matrix.shape[1] == 389
    assert W_s.shape == (1, 1)
    assert W_s[0, 0] == 0.0


def test_tst_ranker_convergence():
    """Verifies Topic-Specific TextRank power iteration convergence (Theorems 1 & 2)."""
    ranker = TopicSpecificTextRank(alpha=1.5, damping=0.85, tol=1e-6, max_iter=500)
    sentences = [
        "mRNA vaccines reduce severe COVID-19 hospitalizations.",
        "FDA approves booster shots for public health.",
        "Politicians held a debate in Washington on budget legislation."
    ]
    n = len(sentences)

    W_s = np.array([
        [0.0, 0.6, 0.1],
        [0.6, 0.0, 0.1],
        [0.1, 0.1, 0.0]
    ])

    lda_dists = [np.array([0.8, 0.2, 0.0]), np.array([0.9, 0.1, 0.0]), np.array([0.1, 0.1, 0.8])]
    u_vec = ranker.compute_topic_relevance_scores(sentences, lda_dists, health_topic_indices=[0])

    results = ranker.rank_sentences(sentences, W_s, u_vec)

    assert results["converged"] is True
    assert results["iterations"] <= 35  # Theorem 2 convergence speed
    assert len(results["ranked_indices"]) == n
    assert results["ranked_indices"][0] in [0, 1]


def test_graph_builder_triples():
    """Verifies fallback Knowledge Graph extraction."""
    builder = KnowledgeGraphBuilder()
    kg = builder.build_knowledge_graph("mRNA vaccines reduce severe COVID-19 hospitalizations.")

    assert "entities" in kg
    assert "triples" in kg
    assert len(kg["triples"]) > 0
    first_triple = kg["triples"][0]
    assert "head" in first_triple
    assert "relation" in first_triple
    assert "tail" in first_triple


def test_graph_rag_jaccard_similarity():
    """Verifies GraphRAG triple Jaccard & Containment Similarity calculation (Section 3.5)."""
    engine = GraphRAGEngine(match_threshold=0.25)

    query_graph = {
        "triples": [
            {"head": "mRNA Vaccine", "relation": "reduces_risk_of", "tail": "Severe Hospitalization"},
            {"head": "CDC", "relation": "recommends", "tail": "mRNA Vaccine"}
        ]
    }

    kb_graph = {
        "topic": "Vaccine Efficacy",
        "triples": [
            {"head": "mRNA Vaccine", "relation": "reduces_risk_of", "tail": "Severe Hospitalization"},
            {"head": "CDC", "relation": "recommends", "tail": "mRNA Vaccine"},
            {"head": "FDA", "relation": "approves", "tail": "mRNA Vaccine"}
        ]
    }

    engine.add_knowledge_graph(kb_graph)
    result = engine.verify_query_graph(query_graph)

    assert result["verdict"] == "True"
    assert result["best_match_score"] >= (2.0 / 3.0)


def test_pipeline_end_to_end():
    """Verifies end-to-end TrumorGPT pipeline fact-checking execution."""
    pipeline = TrumorGPTPipeline(data_dir=os.path.join(base_dir, "data"))
    pipeline.initialize()

    # Test True Claim
    res_true = pipeline.fact_check("mRNA vaccines developed by Pfizer reduce severe COVID-19 hospitalizations.")
    assert res_true["verdict"] == "True"
    assert "explanation" in res_true
    assert "metrics" in res_true
    assert res_true["metrics"]["tst_converged"] is True

    # Test False / Contradictory Claim
    res_false = pipeline.fact_check("Ivermectin is an FDA approved cure for COVID-19.")
    assert res_false["verdict"] == "False"
