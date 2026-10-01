# Error analysis - Set A (LIAR health, n=600)

- Total failures (pred != gold): **600 / 600**

- Abstentions (Undetermined): **599**

- Root cause: the reproduction ships only 8 reference knowledge graphs, so real
  PolitiFact / LIAR health claims have almost no overlap with the KB and the engine
  abstains. The paper's system used a large DBpedia-derived health KB plus GPT-4
  triple extraction, which this environment could not rebuild.

## Failure causes (counts)

- numeric or statistical claim: 252
- named entity / geography not in KB: 170
- knowledge-base coverage gap (no matching health entity/relation): 139
- negation in the claim: 39

## 10 representative failure cases

| # | Gold | Pred | Claim | Extracted query triple | Cause | Suggested improvement |
|---|------|------|-------|------------------------|-------|------------------------|
| 1 | True | Undetermined | The CBO found that the House Republican health care plan would lower premiums by "up to about 10 percent" and, | (Found,associated_with,That) | numeric or statistical claim | add numeric/quantitative KB facts or a numeric verifier |
| 2 | True | Undetermined | According to a recent poll, there are more young Republicans enrolled in their parents (health insurance) plan | (According,associated_with,Recent) | knowledge-base coverage gap (no matching health entity/relation) | ingest DBpedia health triples to raise coverage |
| 3 | True | Undetermined | Obamacare is a massive, massive income redistribution with $250 billion a year in Medicaid expansion (and) in  | (Obamacare,associated_with,Massive) | numeric or statistical claim | add numeric/quantitative KB facts or a numeric verifier |
| 4 | True | Undetermined | Says potential GOP U.S. Senate candidate Tommy Thompson supported Obamacare | (Says,associated_with,Potential) | named entity / geography not in KB | expand KB with policy/political entities |
| 5 | True | Undetermined | With this reform, every insured American gets valuable consumer protections, and every uninsured American can  | (With,associated_with,This) | knowledge-base coverage gap (no matching health entity/relation) | ingest DBpedia health triples to raise coverage |
| 6 | False | Undetermined | You lie! (in response to President Obama saying health reform would not insure illegal immigrants.) | (Response,associated_with,President) | negation in the claim | add negation-aware triple extraction (currently ignored) |
| 7 | False | Undetermined | Weve had the lowest health care inflation in history because of Obamacare. | (Weve,associated_with,Lowest) | named entity / geography not in KB | expand KB with policy/political entities |
| 8 | False | Undetermined | "We actually have not required in this law that you carry health insurance." | (Actually,associated_with,Have) | negation in the claim | add negation-aware triple extraction (currently ignored) |
| 9 | False | Undetermined | Says Donald Trump is a guy who has called for privatization of the Veterans Administration. | (Says,associated_with,Donald) | named entity / geography not in KB | expand KB with policy/political entities |
| 10 | False | Undetermined | Congress has cut funding, has slashed funding, for veterans benefits over these last years. | (Congress,associated_with,Funding) | named entity / geography not in KB | expand KB with policy/political entities |

## Safe fix evaluation

- No automatic fix was applied to the frozen test split. Any change that lifts
  coverage here would require expanding the knowledge base, which risks tuning on
  the evaluation data. The correct next step (documented in the README) is to
  ingest a larger, independently sourced health KB and re-freeze the test set.
