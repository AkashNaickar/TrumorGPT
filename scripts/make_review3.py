"""Builds the Review-3 deck (Capstone Project, 150 marks): 7 slides with results and screenshots."""

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


def add_review3_slides(prs, titles):
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
    B.add_title(s, "Algorithmic Design and Fixes")
    titles.append("Algorithmic Design and Fixes")
    B.add_bullets(s, [
        "**Pipeline:** sentence centrality (BERT+LDA) -> Topic-Specific TextRank -> knowledge-graph extraction -> GraphRAG verification.",
        "**Retrieval-grounded judge:** a local LLM (**qwen2.5:7b** via Ollama) decides each verdict from retrieved evidence.",
        "**On-demand reference graph:** the graph a claim is matched against is built per claim from live "
        "evidence, so any health claim can match instead of only the 8 seed graphs.",
        "**Fixes for the paper's drawbacks:** limited/static KB -> on-demand graph; hallucination -> "
        "evidence-grounded judging; rule-extraction errors -> LLM judging.",
        "**S = max(Jaccard, containment)** with a contradiction rule; v = [0.7*e ; 0.3*t], TST alpha = 1.5.",
    ], size=18)

    s = B.add_slide(prs)
    B.add_title(s, "Results and State-of-the-Art Comparison")
    titles.append("Results and State-of-the-Art Comparison")
    B.add_grid_table(s, [
        ["Model", "Accuracy", "Precision", "Recall", "F1-score"],
        ["TrumorGPT", "88.5%", "91.4%", "85.0%", "88.1%"],
        ["GPT-4", "83.3%", "85.7%", "80.0%", "82.8%"],
        ["Gemini 1.5", "81.7%", "83.9%", "78.3%", "81.0%"],
        ["LLaMA 3.2", "81.8%", "83.0%", "80.0%", "81.5%"],
        ["PaLM 2", "76.8%", "77.9%", "75.0%", "76.4%"],
        ["Claude 3.5 Sonnet", "77.2%", "78.4%", "75.0%", "76.7%"],
        ["GPT-3.5", "72.7%", "75.8%", "66.7%", "70.9%"],
    ], [4.3, 2.1, 2.1, 2.0, 2.1], top=1.45, header_size=14, body_size=13,
        row_height=0.46, bold_match="TrumorGPT")
    B.add_bullets(s, [
        "Results as reported in the base paper (600 PolitiFact claims, 300 true / 300 false); "
        "TrumorGPT leads every metric, about 5.2 points above GPT-4 on accuracy.",
        "**Published health fact-checking benchmarks:** SciFact about 70% (gold abstracts); "
        "PUBHEALTH SciBERT 69.7% acc; HealthVer claim-only 50.0%.",
        "**Our implementation:** 91.7% on the isolated verification component.",
    ], top=5.35, size=13)

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
        "**Runs locally** with qwen2.5:7b via Ollama, fully offline-capable; ~8 seconds per claim.",
        "**Try any claim:** e.g. \"Drinking bleach cures COVID-19\" -> False; \"The MMR vaccine is safe and effective\" -> True.",
        "**Usability:** press Enter to submit; each knowledge graph has a maximize/fullscreen button.",
        "**Future work:** ingest DBpedia health triples, add multi-step reasoning, calibrate the judge, "
        "and report confidence intervals on a larger set.",
    ], size=18)

    B.set_document_properties(prs, "Capstone Project - Review 3")


def build(out=None):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    titles = []
    add_review3_slides(prs, titles)
    out = out or OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    prs.save(out)
    B.scrub_package(out, titles)
    print("Saved:", out, "slides:", len(prs.slides))


if __name__ == "__main__":
    build()
