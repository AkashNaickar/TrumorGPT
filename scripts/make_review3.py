"""Builds the Review-3 deck (Capstone Project, 150 marks) with results and screenshots."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_ppt as B
from pptx import Presentation
from pptx.util import Inches, Pt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
SHOTS = os.path.join(ROOT, "presentation", "shots")
OUT = os.path.join(ROOT, "presentation", "24005_179_review3.pptx")


def load_results():
    with open(os.path.join(BASE, "results", "metrics.json"), encoding="utf-8") as f:
        m = json.load(f)
    hal = {}
    hp = os.path.join(BASE, "results", "hallucination.json")
    if os.path.exists(hp):
        with open(hp, encoding="utf-8") as f:
            hal = json.load(f)
    return m, hal


def add_title_slide(prs, titles):
    s = B.add_slide(prs)
    box = s.shapes.add_textbox(Inches(0.9), Inches(1.7), Inches(11.5), Inches(1.8))
    tf1 = box.text_frame
    tf1.word_wrap = True
    p = tf1.paragraphs[0]
    p.text = "TrumorGPT: GraphRAG Health Fact-Checking"
    p.font.name = B.TITLE_FONT
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = B.DARK
    box2 = s.shapes.add_textbox(Inches(0.9), Inches(3.6), Inches(11.5), Inches(3.0))
    t2 = box2.text_frame
    t2.word_wrap = True
    lines = [
        ("Capstone Project - Review 3", 22, True),
        ("Akash KG  |  Roll No.: CH.SC.U4CSE24005", 20, False),
        ("", 10, False),
        ("Base paper: C. N. Hang, P.-D. Yu, C. W. Tan. IEEE Transactions on Artificial "
         "Intelligence, 6(11), 3148-3162, 2025. DOI: 10.1109/TAI.2025.3567369", 17, False),
    ]
    for i, (line, size, bold) in enumerate(lines):
        pp = t2.paragraphs[0] if i == 0 else t2.add_paragraph()
        pp.text = line
        pp.font.name = B.BODY_FONT
        pp.font.size = Pt(size)
        pp.font.bold = bold
        pp.font.color.rgb = B.DARK if bold else B.BLACK
        pp.space_after = Pt(6)
    titles.append("Title")


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    titles = []
    m, hal = load_results()
    kb = m["kb_component"]["strict"]["accuracy"] * 100
    tf = m["baselines"]["tfidf_lr"]["strict"]["accuracy"] * 100

    add_title_slide(prs, titles)

    s = B.add_slide(prs)
    B.add_title(s, "Problem Identification and Literature Survey")
    titles.append("Problem Identification and Literature Survey")
    B.add_bullets(s, [
        "**Problem:** health misinformation spreads faster than verified facts; manual checking cannot scale.",
        "**Gap 1 - LLMs:** fluent but **hallucinate** and are frozen at a training date.",
        "**Gap 2 - knowledge graphs:** structured but **static and limited** in coverage.",
        "**Gap 3 - standard RAG:** retrieves **text passages**, not relational structure.",
        "**Gap 4 (the paper's):** no method combines an **updatable health KG** with LLM reasoning.",
        "**Future research:** live knowledge freshness, hallucination control, and reasoning over multi-step claims.",
    ], size=19)

    s = B.add_slide(prs)
    B.add_title(s, "Datasets and Data Preprocessing")
    titles.append("Datasets and Data Preprocessing")
    B.add_grid_table(s, [
        ["Dataset", "What it provides", "Preprocessing applied"],
        ["DBpedia", "Structured health facts as RDF triples (English, post-Dec 2023)",
         "Health-keyword filter (health, medical, disease, pandemic...); loaded as the reference base"],
        ["PolitiFact / LIAR", "Fact-checked claims with 6-level ratings (12,836 rows)",
         "Health-care filter (1,434); 6 ratings folded to binary; balanced 300/300 test (seed 42); 834 rows for baseline"],
    ], [1.7, 4.6, 6.2], top=1.6, header_size=14, body_size=13, row_height=1.0)
    B.add_bullets(s, [
        "**Inconsistencies addressed:** label granularity (6 to 2), class imbalance (balanced sampling), "
        "and text noise (URLs and punctuation stripped).",
        "**Feature justification:** sentence embedding + topic vector (0.7/0.3), TST scores, "
        "(head, relation, tail) triples, Jaccard/containment similarity.",
    ], top=4.9, size=15)

    s = B.add_slide(prs)
    B.add_title(s, "Algorithmic Design and Approach")
    titles.append("Algorithmic Design and Approach")
    B.add_bullets(s, [
        "**Pipeline:** sentence centrality (BERT+LDA) -> Topic-Specific TextRank -> knowledge-graph extraction -> GraphRAG verification.",
        "**Retrieval-grounded judge (new):** a local LLM (**qwen2.5:7b** via Ollama) decides the verdict from retrieved evidence.",
        "**Live freshness (new):** Wikipedia evidence is fetched per claim at query time, so the system is not limited to the sealed KG.",
        "**Hallucination control (new):** the system may answer **Undetermined** instead of guessing; every verdict keeps its evidence.",
        "**S = max(Jaccard, containment)** with a contradiction rule; v = [0.7*e ; 0.3*t], TST alpha = 1.5.",
    ], size=18)

    s = B.add_slide(prs)
    B.add_title(s, "Paper Drawbacks vs. Our Fixes")
    titles.append("Paper Drawbacks vs Our Fixes")
    B.add_grid_table(s, [
        ["Drawback in the paper", "Fix in this implementation"],
        ["Static, limited knowledge base (small coverage)", "LLM judge answers any health claim; live Wikipedia evidence at query time"],
        ["LLM hallucination / confident wrong answers", "Evidence-grounded judging plus explicit Undetermined abstention"],
        ["Rule-based triple extraction errors", "LLM judging replaces reliance on the rule triples for the verdict"],
        ["Six-level rating collapsed to binary", "Kept binary for parity; the judge returns a short reason for review"],
        ["Hard to reproduce / no test harness", "Nine tests, seeded evaluation sets, one-command reproduce script"],
    ], [5.6, 7.0], top=1.55, header_size=13.5, body_size=12.5, row_height=0.8)

    s = B.add_slide(prs)
    B.add_title(s, "Results on Benchmarks and Test Cases")
    titles.append("Results on Benchmarks and Test Cases")
    B.add_grid_table(s, [
        ["Test case / benchmark", "Result", "Notes"],
        ["Component verification (KB-grounded, n=48)", f"{kb:.1f}% strict", "100% on committed verdicts; contradiction recall 73.3%"],
        ["End-to-end LIAR health (n=600)", "0% strict, 99.8% abstain", "coverage limit: 8 seed graphs vs the paper's DBpedia base"],
        ["TF-IDF baseline (n=600)", f"{tf:.1f}%", "always-False baseline = 50.0%"],
        ["Ablation: contradiction off", "91.7% -> 68.8%", "contradiction detection is the main contributor"],
        ["Ablation: Jaccard-only", "91.7% -> 77.1%", "max(Jaccard, containment) helps"],
        ["Paper-reported (not reproduced)", "88.5% acc, 88.1% F1", "the paper's own table, different KB and LLM"],
    ], [4.6, 3.0, 5.0], top=1.55, header_size=13, body_size=12.5, row_height=0.72, bold_match="Paper")

    s = B.add_slide(prs)
    B.add_title(s, "Comparison with State-of-the-Art")
    titles.append("Comparison with State-of-the-Art")
    B.add_bullets(s, [
        "**Base paper (same task, 600 claims):** TrumorGPT 88.5% acc, GPT-4 83.3%, "
        "LLaMA 3.2 81.8%, Gemini 1.5 81.7% [paper-reported].",
        "**Published health fact-checking benchmarks:** SciFact about 70% (gold abstracts); "
        "PUBHEALTH SciBERT 69.7% acc; HealthVer claim-only 50.0%.",
        "**LIAR baseline:** majority 20.8% on test; a plain classifier is the weakest reference for this task.",
        "**Our system:** 91.7% on the isolated verification component; end-to-end accuracy is limited by "
        "knowledge-base coverage, not by the algorithm.",
    ], size=17)
    box = s.shapes.add_textbox(Inches(0.8), Inches(6.6), Inches(11.8), Inches(0.7))
    pp = box.text_frame.paragraphs[0]
    pp.text = "Published figures are cited in docs/sources.md; they are not our measurements."
    pp.font.name = B.BODY_FONT
    pp.font.size = Pt(12)
    pp.font.italic = True
    pp.font.color.rgb = B.GRAY

    s = B.add_slide(prs)
    B.add_title(s, "Hallucination Reduction")
    titles.append("Hallucination Reduction")
    a = hal.get("A_plain_llm", {})
    b = hal.get("B_our_system", {})
    B.add_grid_table(s, [
        ["Setting", "Hallucination rate (confident-wrong)", "Coverage", "Source"],
        ["Plain LLM, no retrieval", f"{a.get('hallucination_rate', 0)*100:.1f}%", f"{a.get('coverage', 0)*100:.0f}%", "ours (n=30)"],
        ["Our system (retrieval + abstain)", f"{b.get('hallucination_rate', 0)*100:.1f}%", f"{b.get('coverage', 0)*100:.0f}%", "ours (n=30)"],
        ["AA-Omniscience, published range", "26% to 81% across models", "n/a", "Artificial Analysis"],
        ["RAG vs conventional (cancer Q&A)", "about 40% to 0-6%", "n/a", "JMIR 2025"],
    ], [4.6, 4.2, 1.7, 2.2], top=1.55, header_size=12.5, body_size=12, row_height=0.7)
    B.add_bullets(s, [
        "**Hallucination = confident wrong:** wrong verdicts among the answers the system commits to "
        "(abstentions are not hallucinations).",
        "**Result:** the retrieval-grounded system lowers the confident-wrong rate (43.8% to 33.3%) "
        "by abstaining when evidence is weak.",
        "**Caveat:** 30-claim sample and a 7B local model; the published RAG study shows the same direction more strongly.",
    ], top=5.35, size=14)

    s = B.add_slide(prs)
    B.add_title(s, "Implementation (Live)")
    titles.append("Implementation (Live)")
    left = os.path.join(SHOTS, "result_app.png")
    right = os.path.join(SHOTS, "landing.png")
    if os.path.exists(left):
        s.shapes.add_picture(left, Inches(0.5), Inches(1.7), width=Inches(7.5))
    if os.path.exists(right):
        s.shapes.add_picture(right, Inches(8.2), Inches(1.7), width=Inches(4.6))

    s = B.add_slide(prs)
    B.add_title(s, "Demo and Future Work")
    titles.append("Demo and Future Work")
    B.add_bullets(s, [
        "**Local model:** qwen2.5:7b-instruct via Ollama; the public demo uses the Google AI Studio (Gemini) API.",
        "**Try any claim:** e.g. \"Drinking bleach cures COVID-19\" -> False; \"The MMR vaccine is safe and effective\" -> True.",
        "**Future work:** ingest DBpedia health triples, add multi-step reasoning, calibrate the judge, "
        "and report confidence intervals on a larger set.",
        "**Public URL:** deployed on Vercel (see the homepage link in the repository).",
    ], size=18)

    B.set_document_properties(prs, "Capstone Project - Review 3")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    B.scrub_package(OUT, titles)
    print("Saved:", OUT, "slides:", len(prs.slides))


if __name__ == "__main__":
    build()
