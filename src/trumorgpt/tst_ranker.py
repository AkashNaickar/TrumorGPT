"""
Topic-Specific TextRank (TST) Algorithm (Section 3.3)
Ranks sentences/keywords using a topic-biased Markov chain.
Key Parameters:
- alpha = 1.5 (50% boost to health topics)
- damping factor d = 0.85
- tolerance = 1e-6 in L1 norm
"""

from typing import Any

import numpy as np


class TopicSpecificTextRank:
    def __init__(self, alpha: float = 1.5, damping: float = 0.85, tol: float = 1e-6, max_iter: int = 500):
        self.alpha = alpha
        self.damping = damping
        self.tol = tol
        self.max_iter = max_iter

    def compute_topic_relevance_scores(
        self,
        sentences: list[str],
        lda_topic_distributions: list[np.ndarray],
        health_topic_indices: list[int] | None = None
    ) -> np.ndarray:
        """
        Computes topic relevance vector u = [R(v_1), R(v_2), ..., R(v_n)]
        Assigns alpha = 1.5 multiplier to health topics.
        """
        n = len(sentences)
        if n == 0:
            return np.array([])

        if health_topic_indices is None:
            # Default: treat top topic indices as health topics
            health_topic_indices = [0, 1]

        scores = []
        for dist in lda_topic_distributions:
            # Topic weighting beta_k: alpha for health topics, 1 otherwise
            weighted_sum = 0.0
            for k_idx, val in enumerate(dist):
                beta_k = self.alpha if k_idx in health_topic_indices else 1.0
                weighted_sum += beta_k * val
            scores.append(weighted_sum)

        u = np.array(scores)
        u_sum = np.sum(u)
        if u_sum > 0:
            u = u / u_sum
        else:
            u = np.ones(n) / n

        return u

    def rank_sentences(
        self,
        sentences: list[str],
        similarity_matrix: np.ndarray,
        topic_relevance_vector: np.ndarray
    ) -> dict[str, Any]:
        """
        Runs Topic-Specific TextRank (TST) power iteration algorithm.
        Returns dictionary containing TST scores, ranked indices, iterations, and convergence log.
        """
        n = len(sentences)
        if n == 0:
            return {
                "scores": np.array([]),
                "ranked_indices": [],
                "iterations": 0,
                "converged": True
            }

        if n == 1:
            return {
                "scores": np.array([1.0]),
                "ranked_indices": [0],
                "iterations": 1,
                "converged": True
            }

        u = topic_relevance_vector
        W = similarity_matrix

        # 1. Compute Adjusted Edge Weight Matrix W_prime: w'_j,i = (R(v_i) + R(v_j)) / 2 * w_j,i
        W_prime = np.zeros((n, n))
        for j in range(n):
            for i in range(n):
                W_prime[j, i] = ((u[i] + u[j]) / 2.0) * W[j, i]

        # 2. Compute Column-Stochastic Transition Matrix P: p_i,j = w'_j,i / sum_k(w'_j,k)
        P = np.zeros((n, n))
        for j in range(n):
            col_sum = np.sum(W_prime[j, :])
            if col_sum > 0:
                P[:, j] = W_prime[j, :] / col_sum
            else:
                # If isolated node, teleport according to topic vector u
                P[:, j] = u

        # 3. Transition Matrix P_prime = d * P + (1 - d) * E where E = u * e^T
        E = np.tile(u.reshape(-1, 1), (1, n))
        P_prime = self.damping * P + (1.0 - self.damping) * E

        # 4. Power Iteration
        tst_vec = np.ones(n) / n  # Uniform initial distribution TST^(0)
        converged = False
        iterations = 0

        for it in range(1, self.max_iter + 1):
            prev_tst = tst_vec.copy()
            tst_vec = P_prime @ tst_vec  # Power step: TST^(t+1) = P' * TST^(t)

            diff = np.sum(np.abs(tst_vec - prev_tst))  # L1 norm difference
            iterations = it

            if diff < self.tol:
                converged = True
                break

        ranked_indices = np.argsort(tst_vec)[::-1].tolist()

        return {
            "scores": tst_vec,
            "ranked_indices": ranked_indices,
            "iterations": iterations,
            "converged": converged,
            "topic_relevance_u": u
        }
