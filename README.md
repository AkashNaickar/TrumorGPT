# TrumorGPT

A local, reproducible implementation of a **GraphRAG health fact-checker** based on:

> C. N. Hang, P.-D. Yu, and C. W. Tan, "TrumorGPT: Graph-Based Retrieval-Augmented Large
> Language Model for Fact-Checking," *IEEE Transactions on Artificial Intelligence*,
> vol. 6, no. 11, pp. 3148-3162, Nov. 2025. DOI: 10.1109/TAI.2025.3567369

It ranks the informative sentences of a claim (LDA + BERT centrality, Topic-Specific
TextRank), builds a query knowledge graph from the claim, and verifies it against a set of
reference health knowledge graphs with graph similarity + contradiction detection. Verdicts
are `True`, `False`, or `Undetermined` (abstain).

## Architecture

```
 claim text
   |
   v
 [1] Topic-Enhanced Sentence Centrality   (LDA + BERT, eta = 0.7)     lda_centrality.py
   |
   v
 [2] Topic-Specific TextRank (TST)        (alpha = 1.5, damping = 0.85) tst_ranker.py
   |
   v
 [3] Knowledge Graph Builder              (few-shot LLM | rule fallback) graph_builder.py
   |      Ollama LLaMA 3.1 -> Gemini -> OpenAI -> deterministic fallback
   v
 [4] GraphRAG verification                (Jaccard + containment, contradiction)
   |                                                                graph_rag.py
   v
 verdict in {True, False, Undetermined}
```

`pipeline.py` orchestrates the four components; `app.py` exposes it over FastAPI
(`/health`, `/`, `/app`, `POST /api/v1/fact-check`, `POST /api/v1/seed-graph`).

## Quickstart

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt          # API only
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt      # eval + deck

# tests
.venv\Scripts\python.exe scripts\run_tests.py

# run the API
.venv\Scripts\python.exe -m uvicorn trumorgpt.app:app --app-dir src --port 8077

# full reproduction (downloads LIAR, builds eval sets, evaluates, figures)
pwsh -File scripts\reproduce.ps1
```

## Fact-checking arbitrary claims (coverage)

Out of the box the system only verifies claims that overlap its **8 reference knowledge
graphs**; everything else returns **Undetermined**. To widen coverage you have three options:

1. **LM judge fallback (implemented, opt-in).** When GraphRAG abstains and a LLM backend is
   reachable (and `TRUMORGPT_OFFLINE` is not set), `src/trumorgpt/llm_judge.py` asks the LLM to
   decide. Enable a backend:
   ```powershell
   # Recommended: local, unlimited, private
   ollama serve
   ollama pull llama3.1:8b
   # or set GEMINI_API_KEY / OPENAI_API_KEY in .env
   ```
   Then run the server **without** `TRUMORGPT_OFFLINE`. The verdict's `metrics.verdict_source`
   will read `LLM judge (Ollama|Gemini|OpenAI)`. If no backend answers, it safely stays
   `Undetermined`.
2. **Bigger knowledge base.** Ingest DBpedia health triples, or add graphs at runtime with
   `POST /api/v1/seed-graph`.
3. **Better extraction.** A stronger LLM extractor improves triple quality for both paths.

Caveat: the LLM judge trades coverage for hallucination risk. It is a fallback, not a
replacement for a verified knowledge base, and it should cite evidence and abstain when unsure.

## Results

Two questions are evaluated separately and honestly.

### Set C - GraphRAG component (KB-grounded, isolatable)

Query graphs built directly from the reference KB triples (positives) and their
contradictions (negatives). This isolates the verification logic from the NL extractor.

| Metric | Value |
|--------|-------|
| Strict accuracy (Undetermined = wrong) | **91.7%** (44/48, 95% CI 83.3-97.9) |
| Accuracy on committed verdicts | **100%** (n=44) |
| Contradiction recall | **73.3%** (11/15) |

### Set A - end-to-end on real PolitiFact-derived claims (LIAR health-care, n=600, 300/300)

| System | Strict acc. | Coverage | Determined acc. | Precision | Recall | F1 |
|--------|-------------|----------|-----------------|-----------|--------|----|
| Majority (all False) | 50.0% | 100% | 50.0% | 0.0 | 0.0 | 0.0 |
| TF-IDF + LogisticRegression | **58.8%** | 100% | 58.8% | 0.68 | 0.33 | 0.45 |
| TrumorGPT (this reproduction) | 0.0% | 0.17% | n/a (n=1) | - | - | - |
| Gemini zero-shot (baseline) | not run | - | - | - | - | - |
| TrumorGPT (paper-reported) | 88.5% | - | - | 91.4 | 85.0 | 88.1 |

**Honest reading of Set A.** The full reproduction *abstains* on 99.8% of real health claims:
the engine only commits when a claim graph overlaps the reference KB, and this environment
ships just **8 reference knowledge graphs**. It therefore has almost no coverage of real
PolitiFact claims, whereas the paper's system used a large **DBpedia-derived health KB** and
**GPT-4** triple extraction. The paper number (88.5%) is **paper-reported**, not reproduced
here. We do not claim to match the paper end-to-end; we reproduce and test the mechanism, and
we quantify the gap. See `results/metrics.json` and `results/error_analysis.md`.

### Ablations (Set C unless noted)

| Ablation | Strict accuracy |
|----------|-----------------|
| Similarity = max(Jaccard, containment) (full) | 91.7% |
| Similarity = containment only | 91.7% |
| Similarity = Jaccard only | 77.1% |
| Contradiction detection ON (full) | 91.7% |
| Contradiction detection OFF | 68.8% |
| Match threshold 0.1 / 0.25 / 0.4 / 0.6 | 91.7% (insensitive on this set) |
| eta in {0.5,0.7,0.9} x alpha in {1.0,1.5,2.0} (Set A) | coverage stays 0.0 |

The eta/alpha grid is flat on Set A because the bottleneck there is KB coverage, not sentence
ranking - a useful negative result.

## Data

- **LIAR** (Wang, 2017): 12.8K PolitiFact.com statements with 6-level ratings, fetched from
  `github.com/thiagorainmaker77/liar_dataset`. Filtered to `health-care` (1,434 rows), mapped
  to binary exactly as the paper does, and split into a balanced 600-claim test set (300/300)
  plus an 834-row training pool for the TF-IDF baseline. Full provenance in
  `data/eval/PROVENANCE.md`.
- **Reference KB**: the 8 seed knowledge graphs in `data/seeded_knowledge_base.json`.
- **Not obtained**: the paper's exact 600-claim set and its DBpedia-derived KB.

## What differs from the paper

1. The paper's DBpedia health KB and GPT-4 extractor were not available; we use the repo's 8
   KGs and a deterministic rule-based extractor (or a reachable LLM backend if configured).
2. The paper's exact PolitiFact subset could not be retrieved; LIAR is a real, citable
   PolitiFact-derived substitute with different coverage.
3. Reported metrics are separated into paper-reported vs reproduced in every table.

## Repository layout

```
src/trumorgpt/      pipeline + components (lda_centrality, tst_ranker, graph_builder, graph_rag)
scripts/            run_tests, build_eval_sets, evaluate, error_analysis, make_ppt, reproduce
tests/              unit + robustness tests
data/               health corpus, seed KB, LIAR, built eval sets
results/            metrics.json, predictions CSV, figures, error_analysis.md
demo/               live demo script
```
