"""
Error analysis for the Set A (LIAR health) reproduction run.

Reads results/liar_health_predictions.csv, re-derives the query knowledge graph for a
representative sample, groups failures by cause, and writes results/error_analysis.md.

Failure here means the system abstained (Undetermined) on a claim that has a gold label,
or produced a wrong committed verdict.
"""

import csv
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
os.environ.setdefault("TRUMORGPT_OFFLINE", "1")

from trumorgpt.pipeline import TrumorGPTPipeline  # noqa: E402

RESULTS = os.path.join(BASE, "results")
PRED = os.path.join(RESULTS, "liar_health_predictions.csv")

CAUSE_RULES = [
    ("numeric or statistical claim", lambda t: any(c.isdigit() for c in t)),
    ("negation in the claim", lambda t: any(w in t.lower() for w in
        [" not ", "never", "no ", "doesn't", "didn't", "isn't", "won't", "denied", "false"])),
    ("named entity / geography not in KB", lambda t: any(w in t.lower() for w in
        ["senate", "house", "congress", "governor", "president", "obama", "trump", "romney",
         "bill", "act", "medicare", "medicaid", "obamacare", "affordable care"])),
]


def classify(claim):
    for name, rule in CAUSE_RULES:
        try:
            if rule(claim):
                return name
        except Exception:
            pass
    return "knowledge-base coverage gap (no matching health entity/relation)"


def main():
    with open(PRED, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    failures = [r for r in rows if r["pred"] != r["gold"]]
    by_cause = {}
    for r in failures:
        by_cause.setdefault(classify(r["claim"]), []).append(r)

    pipeline = TrumorGPTPipeline(data_dir=os.path.join(BASE, "data"))
    pipeline.initialize()

    # 10 representative cases, balanced across gold labels
    sample = []
    for gold in ("True", "False"):
        picks = [r for r in failures if r["gold"] == gold][:5]
        sample.extend(picks)

    lines = ["# Error analysis - Set A (LIAR health, n=600)\n",
             f"- Total failures (pred != gold): **{len(failures)} / {len(rows)}**\n",
             f"- Abstentions (Undetermined): **{sum(1 for r in rows if r['pred']=='Undetermined')}**\n",
             "- Root cause: the reproduction ships only 8 reference knowledge graphs, so real\n"
             "  PolitiFact / LIAR health claims have almost no overlap with the KB and the engine\n"
             "  abstains. The paper's system used a large DBpedia-derived health KB plus GPT-4\n"
             "  triple extraction, which this environment could not rebuild.\n",
             "## Failure causes (counts)\n"]
    for cause, items in sorted(by_cause.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"- {cause}: {len(items)}")
    lines.append("\n## 10 representative failure cases\n")
    lines.append("| # | Gold | Pred | Claim | Extracted query triple | Cause | Suggested improvement |")
    lines.append("|---|------|------|-------|------------------------|-------|------------------------|")

    fixes = {
        "numeric or statistical claim": "add numeric/quantitative KB facts or a numeric verifier",
        "negation in the claim": "add negation-aware triple extraction (currently ignored)",
        "named entity / geography not in KB": "expand KB with policy/political entities",
        "knowledge-base coverage gap (no matching health entity/relation)":
            "ingest DBpedia health triples to raise coverage",
    }
    for i, r in enumerate(sample, 1):
        claim = r["claim"].replace("|", "/")[:110]
        try:
            kg = pipeline.kg_builder.build_knowledge_graph(claim)["triples"]
            tri = "; ".join(f"({t['head']},{t['relation']},{t['tail']})" for t in kg[:1])
        except Exception:
            tri = "(none)"
        cause = classify(r["claim"])
        lines.append(f"| {i} | {r['gold']} | {r['pred']} | {claim} | {tri} | {cause} | {fixes.get(cause,'-')} |")

    lines.append("\n## Safe fix evaluation\n")
    lines.append("- No automatic fix was applied to the frozen test split. Any change that lifts\n"
                 "  coverage here would require expanding the knowledge base, which risks tuning on\n"
                 "  the evaluation data. The correct next step (documented in the README) is to\n"
                 "  ingest a larger, independently sourced health KB and re-freeze the test set.\n")

    with open(os.path.join(RESULTS, "error_analysis.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Wrote", os.path.join(RESULTS, "error_analysis.md"))
    print("Failures:", len(failures), "of", len(rows))
    for cause, items in sorted(by_cause.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(items):4d}  {cause}")


if __name__ == "__main__":
    main()
