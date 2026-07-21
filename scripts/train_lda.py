"""
Script to train and save the LDA Topic Model for Topic-Enhanced Sentence Centrality.
"""

import os
import json
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(base_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from trumorgpt.lda_centrality import TopicEnhancedSentenceCentrality


def main():
    data_file = os.path.join(base_dir, "data", "health_corpus.json")
    model_prefix = os.path.join(base_dir, "data", "lda_model")

    print(f"Loading corpus from: {data_file}")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = [a["text"] for a in data.get("articles", [])]
    print(f"Loaded {len(articles)} health training articles.")

    engine = TopicEnhancedSentenceCentrality(eta=0.7, n_topics=5)
    print("Training LDA model (K=5 topics)...")
    engine.train_lda(articles)
    
    print(f"Saving LDA models to: {model_prefix}_*.pkl")
    engine.save(model_prefix)
    print("[SUCCESS] LDA Topic Training Complete!")


if __name__ == "__main__":
    main()
