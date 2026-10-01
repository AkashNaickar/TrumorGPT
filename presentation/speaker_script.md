# Speaker script - TrumorGPT (6-8 minutes)

Numbers marked [paper] are from the base paper; everything else is our reproduction.

---

**Slide 1 - Title (15s)**
"Good morning. I'm Akash, roll number 24005_179. My capstone reproduces and evaluates
TrumorGPT, a GraphRAG health fact-checker from this IEEE TAI 2025 paper. I'll cover the
problem, my understanding, the data, the method, and - most importantly - what I actually
measured."

**Slide 2 - Selection of the Problem (40s)**
"Health misinformation is a real, large-scale problem. The WHO called COVID-19 the first
global infodemic. It matters because false news spreads faster - a Science 2018 study found
false tweets reach 1,500 people about six times faster than true ones. And NewsGuard currently
tracks 3,749 AI content-farm sites, with two-thirds of untrustworthy sites publishing health
misinformation. My scope is deliberately narrow: health claims only, using existing LLMs and
knowledge graphs, so it's feasible without training a new model."

**Slide 3 - Understanding of the Problem (40s)**
"Fact-checking means deciding whether a claim is accurate. Manual checking doesn't scale.
LLMs alone hallucinate and have a frozen knowledge cutoff. Knowledge graphs alone are accurate
but static. The key insight is that these two are complementary: use the LLM to read language
and a knowledge graph to hold verified facts. TrumorGPT does exactly that with GraphRAG, and
importantly it can say 'Undetermined' instead of guessing."

**Slide 4 - Datasets (40s)**
"Two sources. DBpedia supplies structured, machine-readable facts as RDF triples. For claims,
I use PolitiFact statements as ground truth via the LIAR dataset - 12,836 statements, of which
1,434 are health-care. I map the six-level rating to true/false exactly as the paper does, and
build a balanced 600-claim test set - 300 true, 300 false - with a fixed seed. Everything is
documented in data/eval/PROVENANCE.md."

**Slide 5 - Interpretation of the Solution (45s)**
"Here's how it works on one claim: 'Ivermectin is an FDA-approved cure for COVID-19.' The
pipeline extracts the triple (Ivermectin, claimed_treatment_for, COVID-19) and matches it
against the knowledge base, which says the opposite - 'failed clinical trials for COVID-19'.
That contradiction gives a verdict of False. When a claim matches verified facts, the score is
1.00; when nothing overlaps, it returns Undetermined. One subtlety I want to flag: I report
strict accuracy, which counts an abstention as wrong, separately from coverage and
determined-accuracy, because otherwise the numbers are misleading."

**Slide 6 - Feature Selection (35s)**
"The features are: the semantic triple itself; BERT sentence embeddings; LDA topic
distributions; their fusion at 0.7/0.3; Topic-Specific TextRank scores; and graph-similarity
features including a contradiction flag. I chose these to capture meaning, topic relevance, and
relational structure. The ablation on the next-but-one slide shows which of them actually
matter."

**Slide 7 - Literature Survey (40s)**
"This table compares six works: Karadzhov 2017 on web-based fact-checking, Tracy 2019 and
FACE-KEG 2021 on knowledge-graph explanation, RAG in 2020, a 2022 survey, and Edge 2024 on
GraphRAG. None of them combines an updatable health knowledge graph with LLM reasoning for
health-claim verification - that's the gap TrumorGPT targets."

**Slide 8 - Learning Technique (35s)**
"The technique is TrumorGPT: GraphRAG plus a few-shot LLM plus Topic-Specific TextRank.
The LLM builds the claim graph, TST ranks the important sentences, and GraphRAG computes the
similarity and detects contradictions. The justification is that it grounds the model in
updatable facts, needs no retraining, and can run on a local LLM."

**Slide 9 - Our Results (60s) - the key slide**
"Now the honest part. On the component test - where I feed query graphs directly and isolate
the verification logic - I get 91.7% strict accuracy, and 100% accuracy once it commits; that
shows the mechanism works. But end-to-end on the 600 real claims, strict accuracy is 0% with
99.8% abstentions. Why? Because this environment ships only eight reference knowledge graphs,
while the paper used a huge DBpedia-derived health KB plus GPT-4. For reference, a plain
TF-IDF classifier scores 58.8% and majority is 50%. So I do not claim to match the paper's
88.5% - that number is paper-reported. I reproduce and test the mechanism and I quantify the
gap."

**Slide 10 - Ablation and Error Analysis (45s)**
"The ablations are informative. Removing contradiction detection drops accuracy from 91.7% to
68.8% - that's the single most important component. Jaccard-only similarity drops it to 77.1%.
The threshold and the eta/alpha sentence-ranking parameters barely change anything, which tells
us the end-to-end bottleneck is knowledge-base coverage and triple extraction, not sentence
ranking. The error analysis confirms it: of 600 misses, the biggest buckets are numeric claims,
named entities, and plain coverage gaps."

**Slide 11 - Limitations and Future Work (35s)**
"I'm upfront about four limitations: small KB, rule-based extraction instead of GPT-4, a
different and older claim set, and no significance testing. The clear next step is to ingest
DBpedia health triples and a stronger extractor, then re-freeze the test set and re-evaluate."

**Slide 12 - Demo (25s)**
"The demo runs fully offline and deterministically. Five examples: vaccines and diet come back
True, ivermectin and 'COVID-19 causes cancer' come back False, and an out-of-scope claim comes
back Undetermined. All predictions and metrics are saved under results/."

**Slide 13 - Backup (only if asked)**
"This is the confusion matrix: 300 true and 299 false claims abstained, one false claim was
committed and wrong. It makes the coverage story concrete."

**Closing line**
"To summarise: I implemented and tested the full TrumorGPT pipeline, verified the verification
logic component, and measured honestly where a small knowledge base falls short. Thank you."
