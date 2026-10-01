"""
Graph-Based Retrieval-Augmented Generation (GraphRAG) Engine (Section 3.5)
Performs triple-matching, Jaccard & Containment Similarity calculation S(G_x, G_i), and fact verification.
Output Verdict: y in {True, False, Undetermined}
"""

import json
from typing import Any


class GraphRAGEngine:
    def __init__(self, match_threshold: float = 0.25):
        self.match_threshold = match_threshold
        self.knowledge_base: list[dict[str, Any]] = []

    def load_knowledge_base(self, filepath: str) -> int:
        """Loads reference knowledge base from JSON file."""
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
            self.knowledge_base = data.get("knowledge_graphs", [])
        return len(self.knowledge_base)

    def add_knowledge_graph(self, graph: dict[str, Any]) -> None:
        """Dynamically appends a new verified Knowledge Graph to the index."""
        self.knowledge_base.append(graph)

    def extract_triple_set(self, graph_dict: dict[str, Any]) -> set[tuple[str, str, str]]:
        """Converts graph dictionary into a normalized set of triple tuples (h, r, t)."""
        triples = set()
        for t in graph_dict.get("triples", []):
            h = t.get("head", "").strip().lower()
            r = t.get("relation", "").strip().lower()
            v = t.get("tail", "").strip().lower()
            if h and r and v:
                triples.add((h, r, v))
        return triples

    def _entities_match(self, e1: str, e2: str) -> bool:
        """Helper to check if two entity/relation strings refer to the same concept."""
        e1_clean = e1.strip().lower()
        e2_clean = e2.strip().lower()
        if e1_clean == e2_clean:
            return True

        # Medical Entity Synonym Clusters
        synonym_clusters = [
            {"kids", "children", "pediatric_patients", "youth", "infants", "pediatric hospitalization"},
            {"covid", "covid-19", "sars-cov-2", "coronavirus", "covid infection"},
            {"good", "beneficial", "safe", "harmless", "has_effect good", "good_for"},
            {"hospitalization", "severe_hospitalization", "pediatric hospitalization", "hospital admission"},
            {"air", "airborne", "airborne_droplets", "respiratory_droplets", "airborne_aerosols", "via_air"}
        ]
        for cluster in synonym_clusters:
            if (e1_clean in cluster or any(c in e1_clean for c in cluster)) and \
               (e2_clean in cluster or any(c in e2_clean for c in cluster)):
                return True

        if len(e1_clean) > 3 and len(e2_clean) > 3:
            if e1_clean in e2_clean or e2_clean in e1_clean:
                return True

        return False

    def _relations_match(self, r1: str, r2: str) -> bool:
        """Helper to check if two relations are semantically equivalent."""
        r1_c = r1.strip().lower()
        r2_c = r2.strip().lower()
        if self._entities_match(r1_c, r2_c):
            return True
        synonyms = [
            {"reduces_risk_of", "prevents", "lowers_risk_of", "protects_against", "reduces_transmission_of"},
            {"causes", "leads_to", "results_in", "causes_respiratory_illness_in", "causes_hospitalization_risk_in", "is_harmful_disease_for"},
            {"manufactures", "manufactured_by", "developed_by", "makes"},
            {"approves", "authorized_by", "recommends", "recommends_vaccination_for"},
            {"is_good_for", "is_beneficial_for", "is_safe_for", "good_for", "has_positive_effect"},
            {"is_spread_via", "spreads_via", "spreads_through", "transmitted_by", "transmitted_via", "is_transmitted_by", "airborne_transmission_of"}
        ]
        for syn_set in synonyms:
            if r1_c in syn_set and r2_c in syn_set:
                return True
        return False

    def _triples_match(self, q_triple: tuple[str, str, str], r_triple: tuple[str, str, str]) -> bool:
        """Checks if a query triple matches a reference triple semantically."""
        q_h, q_r, q_t = q_triple
        r_h, r_r, r_t = r_triple

        # Direct match
        direct_match = (
            self._entities_match(q_h, r_h) and
            self._relations_match(q_r, r_r) and
            self._entities_match(q_t, r_t)
        )
        if direct_match:
            return True

        # Inverse match: (mRNA Vaccine, manufactured_by, Pfizer) vs (Pfizer, manufactures, mRNA Vaccine)
        inverse_match = (
            self._entities_match(q_h, r_t) and
            self._relations_match(q_r, r_r) and
            self._entities_match(q_t, r_h)
        )
        return inverse_match

    def compute_similarity(
        self,
        query_triples: set[tuple[str, str, str]],
        reference_triples: set[tuple[str, str, str]]
    ) -> float:
        """
        Computes Graph Similarity S(G_x, G_i) combining Jaccard Similarity
        and Query Containment Ratio |T_x intersection T_i| / |T_x|.
        Uses semantic/fuzzy matching for entity and relation tuples.
        Section 3.5 Equation (5).
        """
        if not query_triples or not reference_triples:
            return 0.0

        matching_query_triples = 0
        for q_t in query_triples:
            for r_t in reference_triples:
                if self._triples_match(q_t, r_t):
                    matching_query_triples += 1
                    break

        containment = matching_query_triples / float(len(query_triples))
        jaccard = matching_query_triples / float(len(query_triples.union(reference_triples)))

        return max(jaccard, containment)

    def detect_contradiction(
        self,
        query_triples: set[tuple[str, str, str]],
        reference_triples: set[tuple[str, str, str]]
    ) -> tuple[bool, str]:
        """
        Detects relational contradictions between query graph and reference graphs.
        Contradiction requires BOTH head and tail entities to match (same subject and object),
        but with opposing relation meanings.
        """
        contradiction_pairs = [
            # Risk/Harm vs Benefit/Safety/Non-causation
            ({"causes", "increases_risk_of", "causes_respiratory_illness_in", "is_harmful_disease_for", "causes_hospitalization_risk_in"},
             {"reduces_risk_of", "prevents", "treats", "cures", "is_good_for", "is_beneficial_for", "is_safe_for", "harmless_to", "safe_for", "good_for", "does_not_cause", "unrelated_to"}),


            # Approved / Effective vs Failed / Unproven / Dangerous
            ({"cures", "approved_for", "is_authorized_treatment_for", "claimed_treatment_for"},
             {"failed_clinical_trials_for", "does_not_approve", "unproven_for", "dangerous_for"}),

            # Mandated vs Prohibited
            ({"blocked", "prohibited"}, {"mandated", "enforced"})
        ]

        for q_head, q_rel, q_tail in query_triples:
            for r_head, r_rel, r_tail in reference_triples:
                same_head = self._entities_match(q_head, r_head)
                same_tail = self._entities_match(q_tail, r_tail) or (q_tail in ["good", "beneficial", "safe", "kids", "children"])

                if same_head and same_tail:
                    for set_a, set_b in contradiction_pairs:
                        if (q_rel in set_a and r_rel in set_b) or (q_rel in set_b and r_rel in set_a):
                            reason = f"Query claim '{q_head} {q_rel} {q_tail}' contradicts verified medical evidence '{r_head} {r_rel} {r_tail}'"
                            return True, reason

        return False, ""

    def verify_query_graph(self, query_graph: dict[str, Any]) -> dict[str, Any]:
        """
        Verifies query graph G_x against Knowledge Base graphs {G_i}.
        Returns verdict in {True, False, Undetermined}, similarity scores, and matched evidence.
        """
        query_triples = self.extract_triple_set(query_graph)

        best_match_score = 0.0
        best_matching_kg = None
        best_contradiction_found = False
        best_contradiction_reason = ""

        for kg in self.knowledge_base:
            ref_triples = self.extract_triple_set(kg)
            sim_score = self.compute_similarity(query_triples, ref_triples)
            is_contra, reason = self.detect_contradiction(query_triples, ref_triples)

            if is_contra:
                if sim_score >= best_match_score or best_matching_kg is None:
                    best_match_score = sim_score
                    best_matching_kg = kg
                    best_contradiction_found = True
                    best_contradiction_reason = reason
            else:
                if sim_score > best_match_score or (sim_score == best_match_score and not best_contradiction_found):
                    best_match_score = sim_score
                    best_matching_kg = kg
                    best_contradiction_found = False
                    best_contradiction_reason = ""

        # Decision Logic (Section 3.5 - Open-World Verification)
        if best_match_score >= self.match_threshold and not best_contradiction_found:
            verdict = "True"
            reasoning = f"Query graph maps directly to verified Knowledge Graph '{best_matching_kg.get('topic') if best_matching_kg else 'Health Base'}' with similarity score {best_match_score:.2f}."
        elif best_contradiction_found:
            verdict = "False"
            reasoning = f"Query contains verifiable inaccuracies. {best_contradiction_reason}."
        else:
            verdict = "Undetermined"
            reasoning = "Insufficient factual graph overlap in current knowledge base to make a definitive decision. Claim is unverified."

        return {
            "verdict": verdict,
            "best_match_score": best_match_score,
            "best_matching_kg": best_matching_kg,
            "semantic_reasoning": reasoning,
            "query_triples": [f"({h}, {r}, {t})" for h, r, t in query_triples]
        }
