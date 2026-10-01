"""
Standalone Test Runner for TrumorGPT Backend Prototype
Executes all unit tests and prints verification results.
"""

import os
import sys
import traceback

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from tests.test_trumorgpt import (
    test_graph_builder_triples,
    test_graph_rag_jaccard_similarity,
    test_lda_sentence_centrality,
    test_pipeline_end_to_end,
    test_tst_ranker_convergence,
)


def run_all_tests():
    print("=" * 65)
    print(" RUNNING TRUMORGPT BACKEND VERIFICATION SUITE")
    print("=" * 65)

    tests = [
        ("LDA + Sentence-BERT Centrality Fusion (eta=0.7)", test_lda_sentence_centrality),
        ("Topic-Specific TextRank Convergence (alpha=1.5)", test_tst_ranker_convergence),
        ("Knowledge Graph Extraction (Triples)", test_graph_builder_triples),
        ("GraphRAG Jaccard Similarity Engine", test_graph_rag_jaccard_similarity),
        ("End-to-End TrumorGPT Fact-Checking Pipeline", test_pipeline_end_to_end)
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            print(f"\nRunning: {name} ...")
            test_fn()
            print("  -> [PASS]")
            passed += 1
        except Exception as e:
            print(f"  -> [FAIL]: {e}")
            traceback.print_exc()
            failed += 1

    print("\n" + "-" * 65)
    print(f"Summary: {passed} Passed, {failed} Failed out of {len(tests)} tests.")
    print("=" * 65)


if __name__ == "__main__":
    run_all_tests()
