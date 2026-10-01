"""
TrumorGPT reproduction - evaluation harness.

Runs the full pipeline (offline, deterministic triple extraction) over labelled claim sets,
plus component tests, baselines, and ablations. Saves predictions and metrics to results/.

Usage:
    python scripts/evaluate.py all        # everything, writes results/
    python scripts/evaluate.py e2e        # Set A end-to-end only
    python scripts/evaluate.py kb         # Set C GraphRAG component only
    python scripts/evaluate.py baselines  # majority + TF-IDF + Gemini zero-shot
    python scripts/evaluate.py ablations  # threshold/measure/contradiction + eta/alpha grid

Metric conventions
    y_pred in {True, False, Undetermined}
    strict accuracy : Undetermined counts as incorrect.
    coverage        : fraction of claims the system committed to (True/False).
    determined acc  : accuracy on the committed subset (selective accuracy).
    precision/recall/F1 : computed on the committed subset, positive class = True.
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter

import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

os.environ.setdefault("TRUMORGPT_OFFLINE", "1")

from trumorgpt.pipeline import TrumorGPTPipeline  # noqa: E402
from trumorgpt.graph_rag import GraphRAGEngine  # noqa: E402
from trumorgpt.tst_ranker import TopicSpecificTextRank  # noqa: E402

EVAL_DIR = os.path.join(BASE, "data", "eval")
RESULTS_DIR = os.path.join(BASE, "results")
FIG_DIR = os.path.join(RESULTS_DIR, "figures")
SEED = 42

# ---- paper-reported numbers (Table I) -------------------------------------
PAPER_REPORTED = {
    "TrumorGPT": {"accuracy": 88.5, "precision": 91.4, "recall": 85.0, "f1": 88.1},
    "GPT-3.5": {"accuracy": 72.7, "precision": 75.8, "recall": 66.7, "f1": 70.9},
    "GPT-4": {"accuracy": 83.3, "precision": 85.7, "recall": 80.0, "f1": 82.8},
    "LLaMA 3.2": {"accuracy": 81.8, "precision": 83.0, "recall": 80.0, "f1": 81.5},
    "PaLM 2": {"accuracy": 76.8, "precision": 77.9, "recall": 75.0, "f1": 76.4},
    "Claude 3.5 Sonnet": {"accuracy": 77.2, "precision": 78.4, "recall": 75.0, "f1": 76.7},
    "Gemini 1.5": {"accuracy": 81.7, "precision": 83.9, "recall": 78.3, "f1": 81.0},
}


# --------------------------------------------------------------------------
def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def bootstrap_ci(correct, n_boot=2000, seed=SEED):
    rng = np.random.default_rng(seed)
    correct = np.asarray(correct, dtype=float)
    if len(correct) == 0:
        return [0.0, 0.0]
    boots = [rng.choice(correct, size=len(correct), replace=True).mean() for _ in range(n_boot)]
    return [round(float(np.percentile(boots, 2.5)), 4), round(float(np.percentile(boots, 97.5)), 4)]


def compute_metrics(golds, preds):
    n = len(golds)
    strict_correct = [1 if p == g else 0 for g, p in zip(golds, preds)]
    strict_acc = sum(strict_correct) / n if n else 0.0

    determined = [(g, p) for g, p in zip(golds, preds) if p in ("True", "False")]
    det_correct = [1 if p == g else 0 for g, p in determined]
    det_acc = sum(det_correct) / len(determined) if determined else 0.0

    tp = sum(1 for g, p in determined if p == "True" and g == "True")
    fp = sum(1 for g, p in determined if p == "True" and g == "False")
    fn = sum(1 for g, p in determined if p == "False" and g == "True")
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    conf = Counter(zip(golds, preds))
    return {
        "n": n,
        "strict": {
            "accuracy": round(strict_acc, 4),
            "accuracy_ci95": bootstrap_ci(strict_correct),
            "confusion": {f"{g}->{p}": conf.get((g, p), 0)
                          for g in ("True", "False") for p in ("True", "False", "Undetermined")},
        },
        "coverage": round(len(determined) / n, 4) if n else 0.0,
        "undetermined_rate": round((n - len(determined)) / n, 4) if n else 0.0,
        "determined": {
            "n": len(determined),
            "accuracy": round(det_acc, 4),
            "accuracy_ci95": bootstrap_ci(det_correct),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
    }


# --------------------------------------------------------------------------
def build_pipeline():
    p = TrumorGPTPipeline()
    p.initialize()
    return p


def run_e2e(claims, pipeline):
    rows = []
    for i, c in enumerate(claims):
        t0 = time.perf_counter()
        try:
            res = pipeline.fact_check(c["claim"])
            pred = res["verdict"]
            score = res["metrics"]["accuracy_score"]
            source = res["query_knowledge_graph"]["source"]
        except Exception as e:  # never crash the harness
            pred, score, source = "Undetermined", 0.0, f"ERROR: {e}"
        rows.append({
            "id": c.get("id", i),
            "claim": c["claim"],
            "gold": c["gold"],
            "pred": pred,
            "score": round(float(score), 4),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "extractor": source,
        })
    return rows


def save_predictions(name, rows):
    path = os.path.join(RESULTS_DIR, f"{name}_predictions.csv")
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path


# --------------------------------------------------------------------------
def eval_e2e():
    test = load_jsonl(os.path.join(EVAL_DIR, "liar_health_test.jsonl"))
    pipeline = build_pipeline()
    rows = run_e2e(test, pipeline)
    save_predictions("liar_health", rows)
    m = compute_metrics([r["gold"] for r in rows], [r["pred"] for r in rows])
    m["set"] = "liar_health (Set A, external)"
    m["extractor"] = rows[0]["extractor"]
    m["mean_latency_ms"] = round(float(np.mean([r["latency_ms"] for r in rows])), 1)
    return m


def eval_kb_component(contradiction=True, measure="max", threshold=0.25):
    items = load_jsonl(os.path.join(EVAL_DIR, "kb_graphs.jsonl"))
    engine = GraphRAGEngine(match_threshold=threshold)
    engine.load_knowledge_base(os.path.join(BASE, "data", "seeded_knowledge_base.json"))
    if not contradiction:
        engine.detect_contradiction = lambda *a, **k: (False, "")
    if measure != "max":
        orig = engine.compute_similarity
        if measure == "jaccard":
            def compute_similarity(q, r, engine=engine):
                if not q or not r:
                    return 0.0
                m = sum(1 for qt in q if any(engine._triples_match(qt, rt) for rt in r))
                return m / float(len(q.union(r)))
        else:  # containment
            def compute_similarity(q, r, engine=engine):
                if not q or not r:
                    return 0.0
                m = sum(1 for qt in q if any(engine._triples_match(qt, rt) for rt in r))
                return m / float(len(q))
        engine.compute_similarity = compute_similarity

    golds, preds, details = [], [], []
    for it in items:
        qg = {"triples": it["triples"]}
        res = engine.verify_query_graph(qg)
        golds.append(it["gold"])
        preds.append(res["verdict"])
        details.append({"id": it["id"], "gold": it["gold"], "pred": res["verdict"],
                        "score": round(res["best_match_score"], 3), "kind": it["kind"]})
    m = compute_metrics(golds, preds)
    contras = [d for d in details if d["kind"] == "contradiction"]
    m["set"] = "kb_graphs (Set C, component)"
    m["contradiction_recall"] = round(
        sum(1 for d in contras if d["pred"] == "False") / len(contras), 4) if contras else None
    return m, details


# --------------------------------------------------------------------------
def baseline_majority(golds):
    preds = ["False"] * len(golds)
    return compute_metrics(golds, preds)


def baseline_tfidf():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    train = load_jsonl(os.path.join(EVAL_DIR, "liar_health_train.jsonl"))
    test = load_jsonl(os.path.join(EVAL_DIR, "liar_health_test.jsonl"))
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
    Xtr = vec.fit_transform([r["claim"] for r in train])
    clf = LogisticRegression(max_iter=1000, random_state=SEED)
    clf.fit(Xtr, [1 if r["gold"] == "True" else 0 for r in train])
    Xte = vec.transform([r["claim"] for r in test])
    proba = clf.predict_proba(Xte)[:, 1]
    preds = ["True" if p >= 0.5 else "False" for p in proba]
    m = compute_metrics([r["gold"] for r in test], preds)
    m["set"] = "TF-IDF + LogisticRegression (trained on disjoint LIAR health pool)"
    m["train_n"] = len(train)
    return m


def baseline_gemini(limit=40):
    """Zero-shot LLM baseline. Gracefully returns an 'unavailable' record if the API
    quota is exhausted or the backend cannot be reached (we never fabricate results)."""
    import requests
    from dotenv import load_dotenv
    load_dotenv(os.path.join(BASE, ".env"))
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return {"set": "Gemini zero-shot", "available": False, "error": "no GEMINI_API_KEY"}
    test = load_jsonl(os.path.join(EVAL_DIR, "liar_health_test.jsonl"))
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(test), size=min(limit, len(test)), replace=False)
    model = "gemini-3.8-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    golds, preds, rows = [], [], []
    for k, i in enumerate(idx):
        claim = test[i]["claim"]
        prompt = ("You are a strict fact-checker. Decide if the claim is True or False. "
                  "Reply with exactly one word, True or False.\nClaim: " + claim)
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                                        "thinkingConfig": {"thinkingBudget": 0}}}
        try:
            r = requests.post(url, json=payload, timeout=60)
        except Exception as e:
            return {"set": f"Gemini ({model}) zero-shot", "available": False, "error": str(e)}
        if r.status_code == 429:
            return {"set": f"Gemini ({model}) zero-shot", "available": False,
                    "error": "quota exhausted (HTTP 429)",
                    "note": "free-tier limit reached; baseline not run"}
        if r.status_code != 200:
            return {"set": f"Gemini ({model}) zero-shot", "available": False,
                    "error": f"HTTP {r.status_code}"}
        parts = r.json()["candidates"][0]["content"].get("parts", [])
        txt = parts[0].get("text", "") if parts else ""
        up = txt.strip().upper()
        pred = "True" if "TRUE" in up else ("False" if "FALSE" in up else "Undetermined")
        golds.append(test[i]["gold"])
        preds.append(pred)
        rows.append({"id": test[i]["id"], "claim": claim, "gold": test[i]["gold"],
                     "pred": pred, "model": model})
        time.sleep(3.2)
    m = compute_metrics(golds, preds)
    m["set"] = f"Gemini ({model}) zero-shot, n={len(idx)} subset"
    m["available"] = True
    save_predictions("gemini_zero_shot", rows)
    return m


# --------------------------------------------------------------------------
def ablation_threshold():
    out = {}
    for thr in (0.1, 0.25, 0.4, 0.6):
        m, _ = eval_kb_component(threshold=thr)
        out[f"threshold={thr}"] = m["strict"]["accuracy"]
    return out


def ablation_measure():
    out = {}
    for measure in ("max", "jaccard", "containment"):
        m, _ = eval_kb_component(measure=measure)
        out[f"measure={measure}"] = m["strict"]["accuracy"]
    return out


def ablation_contradiction():
    full, _ = eval_kb_component(contradiction=True)
    off, _ = eval_kb_component(contradiction=False)
    return {"contradiction_on": full["strict"]["accuracy"],
            "contradiction_off": off["strict"]["accuracy"]}


def ablation_eta_alpha(limit=200):
    """Vary eta (LDA weight) and alpha (TST topic boost) on a subset of Set A."""
    test = load_jsonl(os.path.join(EVAL_DIR, "liar_health_test.jsonl"))[:limit]
    out = {}
    for eta in (0.5, 0.7, 0.9):
        for alpha in (1.0, 1.5, 2.0):
            p = build_pipeline()
            p.centrality_engine.eta = eta
            p.tst_engine = TopicSpecificTextRank(alpha=alpha, damping=0.85)
            rows = run_e2e(test, p)
            m = compute_metrics([r["gold"] for r in rows], [r["pred"] for r in rows])
            out[f"eta={eta},alpha={alpha}"] = {
                "strict_accuracy": m["strict"]["accuracy"],
                "coverage": m["coverage"],
            }
    return out


# --------------------------------------------------------------------------
def make_figures(e2e_metrics, baselines, ablations):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(FIG_DIR, exist_ok=True)

    # confusion matrix (strict) for Set A
    conf = e2e_metrics["strict"]["confusion"]
    labels = ["True", "False", "Undetermined"]
    mat = np.array([[conf[f"{g}->{p}"] for p in labels] for g in ("True", "False")])
    fig, ax = plt.subplots(figsize=(5, 3.5))
    im = ax.imshow(mat, cmap="Blues")
    ax.set_xticks(range(3)); ax.set_xticklabels(labels)
    ax.set_yticks(range(2)); ax.set_yticklabels(["True", "False"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("Gold"); ax.set_title("Set A confusion (strict)")
    for i in range(2):
        for j in range(3):
            ax.text(j, i, mat[i, j], ha="center", va="center", color="black")
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "confusion_setA.png"), dpi=150); plt.close(fig)

    # baselines bar
    names, accs = [], []
    for k, v in baselines.items():
        if isinstance(v, dict) and "strict" in v:
            names.append(v.get("set", k)); accs.append(v["strict"]["accuracy"])
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(names, [a * 100 for a in accs], color="#4c72b0")
    ax.set_ylabel("Strict accuracy (%)"); ax.set_ylim(0, 100)
    ax.set_title("Set A: baselines")
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "baselines_setA.png"), dpi=150); plt.close(fig)

    # ablation bars
    fig, ax = plt.subplots(figsize=(6, 3.5))
    keys = list(ablations["kb_measure"].keys())
    vals = [v * 100 for v in ablations["kb_measure"].values()]
    ax.bar(keys, vals, color="#55a868")
    ax.set_ylabel("Component strict accuracy (%)"); ax.set_ylim(0, 105)
    ax.set_title("GraphRAG similarity measure")
    fig.tight_layout(); fig.savefig(os.path.join(FIG_DIR, "ablation_measure.png"), dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["all", "e2e", "kb", "baselines", "ablations"])
    ap.add_argument("--gemini-limit", type=int, default=40)
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    metrics = {}

    if args.command in ("all", "e2e"):
        metrics["e2e"] = eval_e2e()
        print("E2E:", json.dumps(metrics["e2e"], indent=1))

    if args.command in ("all", "kb"):
        kb, details = eval_kb_component()
        metrics["kb_component"] = kb
        save_predictions("kb_component", details)
        print("KB component:", json.dumps(kb, indent=1))

    if args.command in ("all", "baselines"):
        test = load_jsonl(os.path.join(EVAL_DIR, "liar_health_test.jsonl"))
        golds = [r["gold"] for r in test]
        metrics["baselines"] = {
            "majority": baseline_majority(golds),
            "tfidf_lr": baseline_tfidf(),
            "gemini_zero_shot": baseline_gemini(args.gemini_limit),
        }
        print("Baselines:", json.dumps(metrics["baselines"], indent=1))

    if args.command in ("all", "ablations"):
        metrics["ablations"] = {
            "kb_threshold": ablation_threshold(),
            "kb_measure": ablation_measure(),
            "kb_contradiction": ablation_contradiction(),
            "eta_alpha": ablation_eta_alpha(),
        }
        print("Ablations:", json.dumps(metrics["ablations"], indent=1))

    if args.command == "all":
        metrics["paper_reported"] = PAPER_REPORTED

    with open(os.path.join(RESULTS_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print("Wrote", os.path.join(RESULTS_DIR, "metrics.json"))

    if args.command == "all":
        try:
            make_figures(metrics["e2e"], metrics["baselines"], metrics["ablations"])
            print("Wrote figures to", FIG_DIR)
        except Exception as e:
            print("Figure generation failed:", e)


if __name__ == "__main__":
    main()
