"""
Topic-Enhanced Sentence Centrality (Section 3.2)
Combines BERT contextual embeddings with Latent Dirichlet Allocation (LDA) topic distributions.
Formula: v_s = [ eta * e_hat_s ; (1 - eta) * t_hat_s ] with default eta = 0.7
"""

import numpy as np
from typing import List, Tuple
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
from sentence_transformers import SentenceTransformer
import joblib
import os


class TopicEnhancedSentenceCentrality:
    def __init__(self, eta: float = 0.7, n_topics: int = 5, bert_model_name: str = 'all-MiniLM-L6-v2'):
        self.eta = eta
        self.n_topics = n_topics
        self.vectorizer = CountVectorizer(stop_words='english')
        self.lda_model = LatentDirichletAllocation(n_components=n_topics, random_state=42)
        self.is_trained = False

        try:
            self.bert_model = SentenceTransformer(bert_model_name)
        except Exception:
            try:
                self.bert_model = SentenceTransformer(bert_model_name, local_files_only=True)
            except Exception:
                os.environ["HF_HUB_OFFLINE"] = "1"
                self.bert_model = SentenceTransformer(bert_model_name)



    def train_lda(self, documents: List[str]) -> None:
        """Trains the LDA topic model on domain-specific health documents."""
        X = self.vectorizer.fit_transform(documents)
        self.lda_model.fit(X)
        self.is_trained = True

    def get_topic_distribution(self, sentence: str) -> np.ndarray:
        """Computes LDA topic probability vector t_s for a sentence."""
        if not self.is_trained:
            # Fallback uniform topic vector if not trained
            return np.ones(self.n_topics) / self.n_topics
        
        X_vec = self.vectorizer.transform([sentence])
        topic_dist = self.lda_model.transform(X_vec)[0]
        # Avoid division by zero
        if np.sum(topic_dist) == 0:
            topic_dist = np.ones(self.n_topics) / self.n_topics
        return topic_dist

    def compute_sentence_embeddings(self, sentences: List[str]) -> np.ndarray:
        """
        Computes topic-enhanced sentence embeddings v_s for a list of sentences.
        v_s = [ eta * e_hat_s ; (1 - eta) * t_hat_s ]
        """
        if not sentences:
            return np.array([])

        # 1. Compute sentence embeddings e_s (with fallback)
        try:
            if hasattr(self, 'bert_model') and self.bert_model is not None:
                raw_bert_embeddings = self.bert_model.encode(sentences)
            else:
                raise ValueError("No BERT model available")
        except Exception:
            # Fallback TF-IDF vectorizer if SentenceTransformers/PyTorch unavailable
            from sklearn.feature_extraction.text import TfidfVectorizer
            tfidf = TfidfVectorizer().fit_transform(sentences)
            raw_bert_embeddings = tfidf.toarray()
            if raw_bert_embeddings.shape[1] < 10:
                # Pad to 10 dims
                pad_width = 10 - raw_bert_embeddings.shape[1]
                raw_bert_embeddings = np.pad(raw_bert_embeddings, ((0,0), (0, pad_width)), 'constant')

        
        hybrid_embeddings = []
        for idx, sentence in enumerate(sentences):
            e_s = raw_bert_embeddings[idx]
            norm_e = np.linalg.norm(e_s)
            e_hat_s = e_s / norm_e if norm_e > 0 else e_s
            
            # 2. Compute LDA topic vector t_s
            t_s = self.get_topic_distribution(sentence)
            norm_t = np.linalg.norm(t_s)
            t_hat_s = t_s / norm_t if norm_t > 0 else t_s

            # 3. Concatenate weighted vectors: v_s = [ eta * e_hat_s ; (1 - eta) * t_hat_s ]
            v_s = np.concatenate([self.eta * e_hat_s, (1 - self.eta) * t_hat_s])
            hybrid_embeddings.append(v_s)

        return np.array(hybrid_embeddings)

    def compute_similarity_matrix(self, sentences: List[str]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Computes sentence similarity graph adjacency matrix W_s using cosine similarity of v_s.
        Returns (similarity_matrix, hybrid_embeddings)
        """
        v_matrix = self.compute_sentence_embeddings(sentences)
        n = len(sentences)
        if n == 0:
            return np.zeros((0, 0)), v_matrix

        # Cosine similarity matrix W_s
        norms = np.linalg.norm(v_matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        normalized_v = v_matrix / norms
        W_s = np.dot(normalized_v, normalized_v.T)

        # Zero out diagonal (no self-loops)
        np.fill_diagonal(W_s, 0.0)
        # Ensure non-negative edge weights
        W_s = np.maximum(W_s, 0.0)

        return W_s, v_matrix

    def save(self, filepath_prefix: str) -> None:
        """Saves trained models to disk."""
        joblib.dump(self.vectorizer, f"{filepath_prefix}_vec.pkl")
        joblib.dump(self.lda_model, f"{filepath_prefix}_lda.pkl")

    def load(self, filepath_prefix: str) -> None:
        """Loads trained models from disk."""
        if os.path.exists(f"{filepath_prefix}_vec.pkl") and os.path.exists(f"{filepath_prefix}_lda.pkl"):
            self.vectorizer = joblib.load(f"{filepath_prefix}_vec.pkl")
            self.lda_model = joblib.load(f"{filepath_prefix}_lda.pkl")
            self.is_trained = True
