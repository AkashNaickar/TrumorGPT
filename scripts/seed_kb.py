"""
Script to inspect and seed the GraphRAG Knowledge Base.
"""

import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from trumorgpt.graph_rag import GraphRAGEngine


def main():
    kb_file = os.path.join(base_dir, "data", "seeded_knowledge_base.json")
    print(f"Loading Knowledge Base from: {kb_file}")

    engine = GraphRAGEngine(match_threshold=0.25)
    count = engine.load_knowledge_base(kb_file)
    print(f"[SUCCESS] Successfully indexed {count} verified Semantic Health Knowledge Graphs!\n")

    print("=" * 60)
    print(" SEEDED KNOWLEDGE GRAPHS OVERVIEW")
    print("=" * 60)
    for idx, kg in enumerate(engine.knowledge_base, 1):
        print(f"Graph #{idx} [{kg.get('graph_id')}] - Topic: {kg.get('topic')}")
        print(f"  Source : {kg.get('source')}")
        print(f"  Triples: {len(kg.get('triples', []))} facts")
        for t in kg.get("triples", [])[:2]:
            print(f"    - ({t['head']}, {t['relation']}, {t['tail']})")
        print()


if __name__ == "__main__":
    main()
