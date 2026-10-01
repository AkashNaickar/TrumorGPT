"""
Builds the evaluation datasets for the TrumorGPT reproduction.

Set A (external, real): LIAR health-care subset.
    Source: LIAR benchmark (Wang, 2017), 12.8K statements scraped from PolitiFact.com
    (https://github.com/thiagorainmaker77/liar_dataset). We filter statements whose
    `subject` field contains "health-care", map the 6-level PolitiFact rating to binary
    exactly as the base paper does (True/Mostly True/Half True -> True;
    Mostly False/False/Pants on Fire -> False; LIAR's "barely-true" -> False), and sample
    a balanced 300 True / 300 False test set with a fixed seed. The remaining health rows
    form a separate training pool used only by the TF-IDF baseline (no leakage into test).

Set C (component, KB-grounded): query graphs built from the project's own 8 reference
    knowledge graphs (data/seeded_knowledge_base.json). Positives are the KB triples
    themselves (expected verdict True); negatives are the same head/tail with an opposing
    relation (expected verdict False). This isolates the GraphRAG verification logic from
    the natural-language triple extractor. It is a component test, not the paper's dataset.

Outputs (data/eval/):
    liar_health_test.jsonl   {id, claim, gold, label6, subject, split}
    liar_health_train.jsonl  {id, claim, gold, label6, subject, split}
    kb_graphs.jsonl          {id, triples:[{head,relation,tail}], gold, kind}
    PROVENANCE.md
"""

import csv
import json
import os
import random
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIAR_DIR = os.path.join(BASE, "data", "liar")
OUT_DIR = os.path.join(BASE, "data", "eval")
KB_FILE = os.path.join(BASE, "data", "seeded_knowledge_base.json")

SEED = 42
TRUE_LABELS = {"true", "mostly-true", "half-true"}
FALSE_LABELS = {"false", "barely-true", "pants-fire"}


def load_liar():
    rows = []
    for split in ("train", "valid", "test"):
        path = os.path.join(LIAR_DIR, f"{split}.tsv")
        with open(path, encoding="utf-8") as f:
            for r in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if len(r) < 14:
                    continue
                rows.append(
                    {
                        "id": f"{split}:{r[0]}",
                        "label6": r[1].strip().lower(),
                        "claim": r[2].strip(),
                        "subject": r[3].strip(),
                        "split": split,
                    }
                )
    return rows


def is_health(subject: str) -> bool:
    return "health-care" in subject.lower()


def to_binary(label6: str):
    if label6 in TRUE_LABELS:
        return "True"
    if label6 in FALSE_LABELS:
        return "False"
    return None


def build_liar_sets(rows):
    health = [r for r in rows if is_health(r["subject"]) and to_binary(r["label6"])]
    rng = random.Random(SEED)
    by_gold = defaultdict(list)
    for r in health:
        r["gold"] = to_binary(r["label6"])
        by_gold[r["gold"]].append(r)

    n = min(300, len(by_gold["True"]), len(by_gold["False"]))
    test_ids = set()
    for gold in ("True", "False"):
        picked = rng.sample(by_gold[gold], n)
        for p in picked:
            test_ids.add(p["id"])

    test = [r for r in health if r["id"] in test_ids]
    train = [r for r in health if r["id"] not in test_ids]
    rng.shuffle(test)
    rng.shuffle(train)
    return test, train, health


def build_kb_graphs():
    with open(KB_FILE, encoding="utf-8") as f:
        kbs = json.load(f)["knowledge_graphs"]

    opposing = {
        "causes": "does_not_cause",
        "does_not_cause": "causes",
        "causes_respiratory_illness_in": "does_not_cause",
        "is_harmful_disease_for": "is_safe_for",
        "increases_risk_of": "reduces_risk_of",
        "reduces_risk_of": "increases_risk_of",
        "causes_higher_rate_of": "reduces_risk_of",
        "approved_for": "failed_clinical_trials_for",
        "is_authorized_treatment_for": "failed_clinical_trials_for",
        "is_approved_for": "failed_clinical_trials_for",
        "failed_clinical_trials_for": "is_authorized_treatment_for",
        "is_good_for": "is_harmful_disease_for",
        "is_safe_for": "is_harmful_disease_for",
        "is_spread_via": "does_not_cause",
    }

    items = []
    i = 0
    for kg in kbs:
        for t in kg["triples"]:
            i += 1
            items.append(
                {
                    "id": f"kb_pos_{i}",
                    "triples": [{"head": t["head"], "relation": t["relation"], "tail": t["tail"]}],
                    "gold": "True",
                    "kind": "positive",
                    "topic": kg["topic"],
                }
            )
            neg_rel = opposing.get(t["relation"])
            if neg_rel:
                i += 1
                items.append(
                    {
                        "id": f"kb_neg_{i}",
                        "triples": [{"head": t["head"], "relation": neg_rel, "tail": t["tail"]}],
                        "gold": "False",
                        "kind": "contradiction",
                        "topic": kg["topic"],
                    }
                )
    return items


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    rows = load_liar()
    test, train, health = build_liar_sets(rows)
    kb_items = build_kb_graphs()

    write_jsonl(os.path.join(OUT_DIR, "liar_health_test.jsonl"), test)
    write_jsonl(os.path.join(OUT_DIR, "liar_health_train.jsonl"), train)
    write_jsonl(os.path.join(OUT_DIR, "kb_graphs.jsonl"), kb_items)

    label6 = Counter(r["label6"] for r in health)
    with open(os.path.join(OUT_DIR, "PROVENANCE.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Evaluation data provenance\n\n"
            "## Set A - LIAR health-care (external, real)\n"
            "- Source: LIAR benchmark (Wang, 2017), statements scraped from PolitiFact.com.\n"
            "- Files: data/liar/{train,valid,test}.tsv, fetched from\n"
            "  https://github.com/thiagorainmaker77/liar_dataset (raw master branch).\n"
            "- Filter: rows whose `subject` contains 'health-care'.\n"
            "- Binary mapping (as in the base paper): True/Mostly True/Half True -> True;\n"
            "  Mostly False/False/Pants on Fire -> False. LIAR's 'barely-true' -> False.\n"
            f"- Health rows after mapping: {len(health)} (of {len(rows)} LIAR statements).\n"
            f"- 6-level label counts (health only): {dict(label6)}\n"
            f"- Test set: balanced {sum(1 for r in test if r['gold']=='True')} True / "
            f"{sum(1 for r in test if r['gold']=='False')} False, seed {SEED}.\n"
            f"- Training pool (baseline only, disjoint from test): {len(train)} rows.\n\n"
            "## Set C - KB-grounded component test (constructed)\n"
            "- Built from this project's own reference KGs (data/seeded_knowledge_base.json).\n"
            "- Positives: the KB triples themselves (expected True).\n"
            "- Negatives: same head/tail with an opposing relation (expected False).\n"
            "- Purpose: isolate GraphRAG verification from the NL triple extractor.\n"
            f"- Items: {len(kb_items)} ({sum(1 for x in kb_items if x['gold']=='True')} positive / "
            f"{sum(1 for x in kb_items if x['gold']=='False')} contradiction).\n\n"
            "## Not obtained\n"
            "- The paper's exact 600-claim PolitiFact set (Health Care + Coronavirus) could not\n"
            "  be retrieved; LIAR is a real, citable PolitiFact-derived substitute but is a\n"
            "  different (2017-era, US political) sample with no Coronavirus subset.\n"
            "- The paper's DBpedia-derived health knowledge base could not be rebuilt; this\n"
            "  reproduction uses only the 8 reference KGs shipped in the repo.\n"
        )

    print(f"LIAR rows: {len(rows)}; health: {len(health)}")
    print(f"test: {len(test)} (True={sum(1 for r in test if r['gold']=='True')}, "
          f"False={sum(1 for r in test if r['gold']=='False')}); train pool: {len(train)}")
    print(f"kb_graphs: {len(kb_items)}")


if __name__ == "__main__":
    main()
