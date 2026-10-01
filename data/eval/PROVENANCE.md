# Evaluation data provenance

## Set A - LIAR health-care (external, real)
- Source: LIAR benchmark (Wang, 2017), statements scraped from PolitiFact.com.
- Files: data/liar/{train,valid,test}.tsv, fetched from
  https://github.com/thiagorainmaker77/liar_dataset (raw master branch).
- Filter: rows whose `subject` contains 'health-care'.
- Binary mapping (as in the base paper): True/Mostly True/Half True -> True;
  Mostly False/False/Pants on Fire -> False. LIAR's 'barely-true' -> False.
- Health rows after mapping: 1434 (of 12836 LIAR statements).
- 6-level label counts (health only): {'false': 332, 'mostly-true': 217, 'barely-true': 287, 'half-true': 282, 'pants-fire': 151, 'true': 165}
- Test set: balanced 300 True / 300 False, seed 42.
- Training pool (baseline only, disjoint from test): 834 rows.

## Set C - KB-grounded component test (constructed)
- Built from this project's own reference KGs (data/seeded_knowledge_base.json).
- Positives: the KB triples themselves (expected True).
- Negatives: same head/tail with an opposing relation (expected False).
- Purpose: isolate GraphRAG verification from the NL triple extractor.
- Items: 48 (33 positive / 15 contradiction).

## Not obtained
- The paper's exact 600-claim PolitiFact set (Health Care + Coronavirus) could not
  be retrieved; LIAR is a real, citable PolitiFact-derived substitute but is a
  different (2017-era, US political) sample with no Coronavirus subset.
- The paper's DBpedia-derived health knowledge base could not be rebuilt; this
  reproduction uses only the 8 reference KGs shipped in the repo.
