"""
Interactive Command Line Fact-Checker for TrumorGPT.
Run this script to test fact-checking queries interactively in the terminal!
"""

import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from trumorgpt.pipeline import TrumorGPTPipeline


def main():
    print("=" * 70)
    print(" TRUMORGPT: GRAPH-BASED RETRIEVAL-AUGMENTED FACT-CHECKER (IEEE 2025)")
    print("=" * 70)
    print("Initializing pipeline, LDA topic model, and GraphRAG Knowledge Base...\n")

    pipeline = TrumorGPTPipeline(data_dir=os.path.join(base_dir, "data"))
    pipeline.initialize()

    print("[SYSTEM READY] Enter health claims to fact-check (type 'exit' or 'q' to quit).\n")

    test_queries = [
        "mRNA vaccines developed by Pfizer reduce severe COVID-19 hospitalizations.",
        "Ivermectin is an FDA-approved cure for treating COVID-19.",
        "Maintaining a balanced diet helps manage blood glucose in type 2 diabetes.",
        "Governor Ron DeSantis signed legislation in Florida to block mandatory vaccine mandates."
    ]

    print("SAMPLE DEMO CLAIMS YOU CAN TRY:")
    for idx, q in enumerate(test_queries, 1):
        print(f"  [{idx}] {q}")
    print("-" * 70)

    while True:
        try:
            user_input = input("\nEnter Health Claim > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "q", "quit"]:
                print("Exiting TrumorGPT CLI. Goodbye!")
                break

            result = pipeline.fact_check(user_input)

            verdict = result["verdict"]
            badge = "TRUE (VERIFIED TRUMOR)" if verdict == "True" else ("FALSE (MISINFORMATION)" if verdict == "False" else "UNDETERMINED")

            print("\n" + "=" * 70)
            print(f" VERDICT: {badge}")
            print("=" * 70)
            print(f"Explanation:\n{result['explanation']}\n")
            
            print(f"Graph Similarity Score : {result['metrics']['accuracy_score']:.4f}")
            print(f"Extracted Graph Source : {result['query_knowledge_graph']['source']}")
            print(f"TST Power Iterations   : {result['metrics']['tst_iterations']} (Converged: {result['metrics']['tst_converged']})")
            
            print("\nExtracted Query Triples (G_x):")
            for t in result['query_knowledge_graph']['triples']:
                print(f"  - ({t['head']}) --[{t['relation']}]--> ({t['tail']})")

            if result.get("evidence_knowledge_graph"):
                ev = result["evidence_knowledge_graph"]
                print(f"\nMatched Knowledge Graph Evidence (G_i: '{ev.get('topic')}'):")
                for t in ev.get("triples", [])[:4]:
                    print(f"  - ({t['head']}) --[{t['relation']}]--> ({t['tail']})")

            print("-" * 70)

        except KeyboardInterrupt:
            print("\nExiting TrumorGPT CLI. Goodbye!")
            break
        except Exception as e:
            print(f"Error during fact-checking: {e}")


if __name__ == "__main__":
    main()
