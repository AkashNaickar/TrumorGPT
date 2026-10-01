# Q&A preparation - 25 likely questions

Answers are grounded in `results/metrics.json` and `results/error_analysis.md`.
⚠ marks answers where you must NOT overclaim.

1. **What problem does this solve?** Automated fact-checking of health claims, where
   misinformation spreads fast and manual checking cannot scale.
2. **Why combine an LLM with a knowledge graph?** LLMs handle language but hallucinate and
   have a frozen cutoff; KGs hold verified, updatable facts. Together they cover each other's
   weakness.
3. **What is GraphRAG?** Retrieval-augmented generation where the retrieved unit is a
   knowledge graph (triples), not text passages, so retrieval is structured and relational.
4. **Why LDA *and* BERT for sentence centrality?** BERT captures semantics; LDA captures the
   health topic. We fuse them at 0.7/0.3 (eta = 0.7).
5. **Why Topic-Specific TextRank and not plain TextRank?** Plain TextRank favours frequent
   words; TST adds a topic boost (alpha = 1.5) so health content is prioritised.
6. **What does a verdict of "Undetermined" mean?** The claim graph does not sufficiently
   overlap the knowledge base, so the system abstains instead of guessing.
7. **How do you score "Undetermined"?** Two ways: strict accuracy (abstention = wrong) and
   coverage + determined-accuracy (selective). We report both.
8. **What were your headline numbers?** Component (Set C): 91.7% strict, 100% on committed,
   contradiction recall 73.3%. End-to-end (Set A, n=600): 0% strict, 99.8% abstention.
9. **Did you reproduce the paper's 88.5%?** ⚠ No - that is paper-reported. We could not obtain
   the paper's DBpedia KB or a GPT-class LLM. Say this plainly.
10. **Why is end-to-end accuracy 0%?** Only 8 reference KGs are shipped, so real claims have
    almost no KB overlap and the engine abstains. It is a coverage limit, not a logic bug.
11. **Which component matters most?** Contradiction detection: removing it drops component
    accuracy from 91.7% to 68.8%.
12. **Which similarity measure?** max(Jaccard, containment) = 91.7%; Jaccard-only = 77.1%;
    containment-only = 91.7%.
13. **Is the threshold sensitive?** No - 0.1 through 0.6 all give 91.7% on Set C.
14. **Did eta and alpha matter?** On Set A they did not change coverage (stayed 0.0). The
    bottleneck is KB coverage, not ranking.
15. **What data did you use?** LIAR (PolitiFact-derived), 12,836 statements; 1,434 health-care;
    balanced 600-claim test (300/300), fixed seed. Provenance in data/eval/PROVENANCE.md.
16. **Is LIAR the same as the paper's dataset?** No. It is a real, citable PolitiFact-derived
    substitute but a different, older (2007-2016) US-political sample with no Coronavirus
    subset.
17. **What baselines did you run?** Majority (50.0%) and TF-IDF + logistic regression (58.8%).
    A Gemini zero-shot baseline was attempted but the free-tier quota was exhausted; we report
    it as not run rather than invent a number.
18. **Could you have tuned to get higher numbers?** We deliberately did not tune on the test
    set; any coverage fix requires expanding the KB, which we froze to avoid leakage.
19. **What are the main failure modes?** Numeric/statistical claims (252), named
    entities/geography (170), KB-coverage gaps (139), negation (39).
20. **Why not just use GPT-4?** Not available in this environment; the pipeline supports
    Ollama/Gemini/OpenAI but falls back to a deterministic rule-based extractor.
21. **What are the ethical risks of automated fact-checking?** Wrong verdicts can suppress true
    claims; the system should abstain and cite evidence, and never be the sole arbiter. This is
    why "Undetermined" exists.
22. **How would you scale this?** Ingest DBpedia health triples, add a stronger LLM extractor,
    cache embeddings, and re-freeze the test set for re-evaluation.
23. **What is your confidence in the results?** Component results have tight CIs on a small
    set; the Set A result is a clear coverage ceiling. We report 95% bootstrap CIs in
    metrics.json.
24. **What did you build that is yours?** The working pipeline, the evaluation harness, the
    reproducibility script, the tests, the ablations, and the datasets - plus the honest
    measurement of where the reproduction matches and where it does not.
25. **What would you do with more time?** Rebuild a DBpedia health KB, run a GPT-class
    extractor, add calibration and significance testing, then report accuracy with CIs.

## Do-not-overclaim reminders
- Never say "we achieved 88.5%". Say "the paper reports 88.5%; we reproduce the mechanism".
- Never present Set C (48 items) as general fact-checking accuracy; it is a component test.
- Always state the n and the metric convention (strict vs determined).
