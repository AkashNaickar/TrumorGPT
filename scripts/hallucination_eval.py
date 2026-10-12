"""
Measures hallucination rate on a labelled health-claim sample.

Two conditions on the same balanced sample from the LIAR health set:
  A. plain LLM, no retrieval, forced True/False  -> "confident wrong" is its error rate.
  B. our system (retrieval-grounded judge that may abstain).

Definitions (following AA-Omniscience): hallucination rate = wrong / (wrong + correct)
among the answers the model actually commits to. Abstentions are not counted as
hallucinations; they reduce coverage instead.

Writes results/hallucination.json and results/hallucination_predictions.csv.
"""

import csv
import json
import os
import sys
import time

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))
os.environ.pop("TRUMORGPT_OFFLINE", None)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE, ".env"))
from trumorgpt.llm_judge import LLMJudge
from trumorgpt.pipeline import TrumorGPTPipeline

SEED = 42
N_PER_CLASS = 15
TEST = os.path.join(BASE, "data", "eval", "liar_health_test.jsonl")
RESULTS = os.path.join(BASE, "results")


def sample():
    rows = [json.loads(x) for x in open(TEST, encoding="utf-8") if x.strip()]
    rng = np.random.default_rng(SEED)
    out = []
    for gold in ("True", "False"):
        idx = [i for i, r in enumerate(rows) if r["gold"] == gold]
        pick = rng.choice(idx, size=min(N_PER_CLASS, len(idx)), replace=False)
        out.extend(rows[i] for i in pick)
    return out


def score(pairs):
    n = len(pairs)
    committed = [(g, p) for g, p in pairs if p in ("True", "False")]
    correct = sum(1 for g, p in committed if g == p)
    wrong = len(committed) - correct
    return {
        "n": n,
        "accuracy_strict": round(len([1 for g, p in pairs if g == p]) / n, 4),
        "coverage": round(len(committed) / n, 4),
        "committed": len(committed),
        "correct": correct,
        "wrong": wrong,
        "hallucination_rate": round(wrong / (wrong + correct), 4) if committed else None,
    }


def main():
    rows = sample()
    judge = LLMJudge()

    print("condition A: plain LLM, no retrieval")
    plain = []
    for r in rows:
        v = judge.judge(r["claim"])            # no evidence
        pred = v["verdict"] if v else "Undetermined"
        plain.append((r["gold"], pred))
        print("  A", r["gold"], pred, r["claim"][:60])

    print("condition B: our system (retrieval + abstain)")
    pipeline = TrumorGPTPipeline()
    pipeline.initialize()
    system = []
    preds_csv = []
    for r in rows:
        t = time.time()
        res = pipeline.fact_check(r["claim"])
        pred = res["verdict"]
        system.append((r["gold"], pred))
        preds_csv.append({"id": r["id"], "claim": r["claim"], "gold": r["gold"],
                          "pred": pred, "source": res["metrics"]["verdict_source"],
                          "evidence": res["metrics"]["evidence_used"],
                          "latency_s": round(time.time() - t, 1)})
        print("  B", r["gold"], pred, r["claim"][:60])

    out = {"n_per_condition": len(rows),
           "A_plain_llm": score(plain),
           "B_our_system": score(system)}
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "hallucination.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    with open(os.path.join(RESULTS, "hallucination_predictions.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(preds_csv[0].keys()))
        w.writeheader()
        w.writerows(preds_csv)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
