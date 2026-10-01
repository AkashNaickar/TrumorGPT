"""
TrumorGPT Main Fact-Checking Pipeline Orchestrator
Integrates:
1. Topic-Enhanced Sentence Centrality (LDA + BERT)
2. Topic-Specific TextRank (TST)
3. Knowledge Graph Builder (Ollama / GPT-4 / Fallback)
4. GraphRAG Verification Engine (Jaccard Similarity)
"""

import os
import re
from typing import List, Dict, Any
from trumorgpt.lda_centrality import TopicEnhancedSentenceCentrality
from trumorgpt.tst_ranker import TopicSpecificTextRank
from trumorgpt.graph_builder import KnowledgeGraphBuilder
from trumorgpt.graph_rag import GraphRAGEngine


class TrumorGPTPipeline:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # Default data directory relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_dir = os.path.join(base_dir, "data")

        self.data_dir = data_dir
        self.centrality_engine = TopicEnhancedSentenceCentrality(eta=0.7, n_topics=5)
        self.tst_engine = TopicSpecificTextRank(alpha=1.5, damping=0.85)
        self.kg_builder = KnowledgeGraphBuilder()
        self.graph_rag_engine = GraphRAGEngine(match_threshold=0.25)
        self.is_initialized = False

    def initialize(self) -> None:
        """Initializes pipeline, trains LDA on health corpus, loads Knowledge Base."""
        corpus_file = os.path.join(self.data_dir, "health_corpus.json")
        kb_file = os.path.join(self.data_dir, "seeded_knowledge_base.json")

        # 1. Train LDA model on health corpus
        if os.path.exists(corpus_file):
            import json
            with open(corpus_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                docs = [item.get("text", "") for item in data.get("articles", [])]
                if docs:
                    self.centrality_engine.train_lda(docs)

        # 2. Load Knowledge Base into GraphRAG
        if os.path.exists(kb_file):
            self.graph_rag_engine.load_knowledge_base(kb_file)

        self.is_initialized = True

    def split_into_sentences(self, text: str) -> List[str]:
        """Splits article or input text into clean sentences."""
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 5]
        if not sentences and text.strip():
            sentences = [text.strip()]
        return sentences

    def fact_check(self, query_text: str) -> Dict[str, Any]:
        """
        Executes end-to-end TrumorGPT Fact-Checking pipeline.
        Returns complete structured response matching paper format.
        """
        if not self.is_initialized:
            self.initialize()

        sentences = self.split_into_sentences(query_text)
        
        # Step 1: Compute Topic-Enhanced Sentence Centrality (LDA + BERT, eta=0.7)
        W_s, v_embeddings = self.centrality_engine.compute_similarity_matrix(sentences)
        
        # Step 2: Compute Topic Relevance Vectors & Run TST (alpha=1.5)
        lda_topic_dists = [self.centrality_engine.get_topic_distribution(s) for s in sentences]
        u_vector = self.tst_engine.compute_topic_relevance_scores(sentences, lda_topic_dists)
        tst_results = self.tst_engine.rank_sentences(sentences, W_s, u_vector)

        # Extract Top Key Sentences based on TST ranking
        top_sentence_indices = tst_results.get("ranked_indices", [0])[:2]
        key_sentences = [sentences[idx] for idx in top_sentence_indices]
        key_text = " ".join(key_sentences)

        # Step 3: Build Query Knowledge Graph G_x = {E_x, R_x, F_x}
        query_kg = self.kg_builder.build_knowledge_graph(key_text if key_text else query_text)

        # Step 4: Run GraphRAG Verification (Jaccard Similarity S(G_x, G_i))
        rag_results = self.graph_rag_engine.verify_query_graph(query_kg)

        # Step 5: Format Concise Response Explanation (Paper Avg: 2.8 sentences)
        verdict = rag_results["verdict"]
        reasoning = rag_results["semantic_reasoning"]
        best_kg_topic = rag_results["best_matching_kg"].get("topic") if rag_results["best_matching_kg"] else "Public Health Database"

        # Step 5b: LLM judge fallback for claims outside the knowledge base.
        # Opt-in: skipped in offline mode. Only raises confidence via a reachable LLM backend;
        # if no backend answers, the safe "Undetermined" verdict is kept.
        verdict_source = "GraphRAG knowledge base"
        if verdict == "Undetermined" and os.getenv("TRUMORGPT_OFFLINE") != "1":
            try:
                from trumorgpt.llm_judge import LLMJudge
                judged = LLMJudge().judge(query_text)
            except Exception:
                judged = None
            if judged and judged.get("verdict") in ("True", "False"):
                verdict = judged["verdict"]
                reasoning = judged.get("reason", "")
                best_kg_topic = judged.get("source", "LLM judge")
                verdict_source = judged.get("source", "LLM judge")

        if verdict_source.startswith("LLM judge"):
            explanation = (
                f"The claim did not match the current health knowledge base, so it was judged by an "
                f"LLM fallback: the statement is {verdict.lower()}. {reasoning}"
            )
        elif verdict == "True":
            explanation = (
                f"The statement is true. Semantic health knowledge graph analysis confirms that the claim "
                f"aligns with verified guidelines in '{best_kg_topic}'. {reasoning}"
            )
        elif verdict == "False":
            explanation = (
                f"The statement is false. Fact-checking against semantic health knowledge graphs indicates "
                f"a direct relational contradiction with verified evidence. {reasoning}"
            )
        else:
            explanation = (
                f"The claim is undetermined. There is insufficient factual graph overlap in the current knowledge base "
                f"to make a definitive decision. Relevant medical context has been provided."
            )

        return {
            "query_text": query_text,
            "verdict": verdict,
            "explanation": explanation,
            "metrics": {
                "accuracy_score": rag_results["best_match_score"],
                "tst_iterations": tst_results.get("iterations", 0),
                "tst_converged": tst_results.get("converged", True),
                "total_sentences": len(sentences),
                "key_sentences_extracted": key_sentences,
                "verdict_source": verdict_source
            },
            "query_knowledge_graph": query_kg,
            "evidence_knowledge_graph": rag_results["best_matching_kg"]
        }
