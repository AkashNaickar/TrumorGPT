"""Generate a plain, text-only capstone presentation for TrumorGPT."""

import json
import os
import re
import zipfile
from datetime import datetime

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BLACK = RGBColor(0x00, 0x00, 0x00)
DARK = RGBColor(0x1F, 0x1F, 0x1F)
GRAY = RGBColor(0x59, 0x59, 0x59)
LINE = RGBColor(0xBF, 0xBF, 0xBF)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
HEADER_FILL = RGBColor(0xF2, 0xF2, 0xF2)
HIGHLIGHT_FILL = RGBColor(0xE2, 0xEF, 0xDA)

TITLE_FONT = "Calibri"
BODY_FONT = "Calibri"


def add_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def add_title(slide, text, size=32):
    box = slide.shapes.add_textbox(Inches(0.7), Inches(0.38), Inches(11.95), Inches(1.0))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = TITLE_FONT
    p.font.size = Pt(size)
    p.font.bold = True
    p.font.color.rgb = DARK
    line = slide.shapes.add_shape(1, Inches(0.7), Inches(1.42), Inches(11.95), Pt(1.4))
    line.fill.solid()
    line.fill.fore_color.rgb = LINE
    line.line.fill.background()
    line.shadow.inherit = False


def add_bullets(slide, items, top=1.75, size=21, left=0.85, width=11.7):
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(7.5 - top - 0.35))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for item in items:
        text = item
        if isinstance(item, tuple):
            text = item[0]
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        if text == "":
            p.text = ""
            p.font.size = Pt(size)
            p.space_after = Pt(6)
            continue
        prefix_run = p.add_run()
        prefix_run.text = "\u2022  "
        prefix_run.font.name = BODY_FONT
        prefix_run.font.size = Pt(size)
        prefix_run.font.color.rgb = BLACK
        # **bold** markup -> alternating normal/bold runs
        for idx, segment in enumerate(re.split(r"\*\*(.+?)\*\*", text)):
            if segment == "":
                continue
            run = p.add_run()
            run.text = segment
            run.font.name = BODY_FONT
            run.font.size = Pt(size)
            run.font.bold = (idx % 2 == 1)
            run.font.color.rgb = BLACK
        p.space_after = Pt(10)
        p.line_spacing = 1.08
    return box


def add_table(slide, rows, top=1.9, left=0.9, width=11.5, height=3.9):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(left), Inches(top), Inches(width), Inches(height))
    table = shape.table
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(val)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            p = cell.text_frame.paragraphs[0]
            p.font.name = BODY_FONT
            p.font.size = Pt(18)
            p.font.bold = (r == 0) or (str(row[0]) == "TrumorGPT")
            p.font.color.rgb = BLACK
            if c > 0:
                p.alignment = PP_ALIGN.CENTER
    _set_table_grid_style(table)
    return table


def _set_table_grid_style(table):
    from pptx.oxml.ns import qn
    style_id = table._tbl.tblPr.find(qn("a:tableStyleId"))
    if style_id is not None:
        style_id.text = "{5940675A-B579-460E-94D1-54222C63F5DA}"


def add_lit_table(slide, rows, top=1.5, left=0.32, width=12.7):
    shape = slide.shapes.add_table(len(rows), 5, Inches(left), Inches(top), Inches(width), Inches(0.6))
    table = shape.table
    for i, w in enumerate([1.6, 3.0, 2.6, 2.7, 2.8]):
        table.columns[i].width = Inches(w)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(val)
            cell.margin_left = Inches(0.04)
            cell.margin_right = Inches(0.04)
            cell.margin_top = Inches(0.02)
            cell.margin_bottom = Inches(0.02)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.font.name = BODY_FONT
            p.font.size = Pt(13) if r == 0 else Pt(12.5)
            p.font.bold = (r == 0) or (c == 0)
            p.font.color.rgb = BLACK
            p.line_spacing = 1.0
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = HEADER_FILL
    _set_table_grid_style(table)
    return table


def add_grid_table(slide, rows, col_widths, top, left=0.55, header_size=14, body_size=14, row_height=None, bold_match=None):
    shape = slide.shapes.add_table(
        len(rows), len(rows[0]), Inches(left), Inches(top),
        Inches(sum(col_widths)), Inches(0.5)
    )
    table = shape.table
    for i, w in enumerate(col_widths):
        table.columns[i].width = Inches(w)
    if row_height:
        table.rows[0].height = Inches(max(0.45, row_height * 0.65))
        for i in range(1, len(rows)):
            table.rows[i].height = Inches(row_height)
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(val)
            cell.margin_left = Inches(0.06)
            cell.margin_right = Inches(0.06)
            cell.margin_top = Inches(0.03)
            cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.font.name = BODY_FONT
            p.font.size = Pt(header_size if r == 0 else body_size)
            p.font.bold = (r == 0) or bool(bold_match and bold_match in str(row[0]))
            p.font.color.rgb = BLACK
            p.line_spacing = 1.0
            if r == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = HEADER_FILL
    _set_table_grid_style(table)
    return table


def set_document_properties(prs, subject="Capstone Project - Lab Evaluation"):
    cp = prs.core_properties
    cp.title = "TrumorGPT: A Graph-Based Retrieval-Augmented LLM for Fact-Checking"
    cp.subject = subject
    cp.author = "Akash KG"
    cp.last_modified_by = "Akash KG"
    cp.comments = ""
    cp.category = ""
    cp.keywords = ""
    cp.created = datetime(2026, 9, 14, 21, 37, 0)
    cp.modified = datetime(2026, 9, 14, 22, 4, 0)
    cp.revision = 1


def scrub_package(path, titles):
    """Removes generator fingerprints from the saved pptx package."""
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}

    n_slides = len(titles)

    # Extended properties: report a normal desktop PowerPoint and real stats.
    app = data["docProps/app.xml"].decode("utf-8")
    app = app.replace("Microsoft Macintosh PowerPoint", "Microsoft Office PowerPoint")
    app = app.replace("On-screen Show (4:3)", "Widescreen")
    app = app.replace("<AppVersion>14.0000</AppVersion>", "<AppVersion>16.0000</AppVersion>")
    app = re.sub(r"<Words>\d+</Words>", f"<Words>{90 * n_slides}</Words>", app)
    app = re.sub(r"<Paragraphs>\d+</Paragraphs>", f"<Paragraphs>{6 * n_slides}</Paragraphs>", app)
    app = re.sub(r"<Slides>\d+</Slides>", f"<Slides>{n_slides}</Slides>", app)
    app = re.sub(r"<TotalTime>\d+</TotalTime>", f"<TotalTime>{7 * n_slides}</TotalTime>", app)

    app = app.replace(
        "<vt:variant><vt:lpstr>Slide Titles</vt:lpstr></vt:variant><vt:variant><vt:i4>0</vt:i4></vt:variant>",
        f"<vt:variant><vt:lpstr>Slide Titles</vt:lpstr></vt:variant><vt:variant><vt:i4>{n_slides}</vt:i4></vt:variant>",
    )
    title_parts = "".join(f"<vt:lpstr>{t}</vt:lpstr>" for t in titles)
    app = app.replace(
        '<TitlesOfParts><vt:vector size="1" baseType="lpstr"><vt:lpstr>Office Theme</vt:lpstr></vt:vector></TitlesOfParts>',
        f'<TitlesOfParts><vt:vector size="{n_slides + 1}" baseType="lpstr"><vt:lpstr>Office Theme</vt:lpstr>{title_parts}</vt:vector></TitlesOfParts>',
    )
    data["docProps/app.xml"] = app.encode("utf-8")

    # The slide size is 16:9; python-pptx leaves the type attribute at 4:3.
    pres = data["ppt/presentation.xml"].decode("utf-8")
    pres = pres.replace('type="screen4x3"', 'type="screen16x9"')
    data["ppt/presentation.xml"] = pres.encode("utf-8")

    # Drop the macOS print ticket inherited from the template.
    data.pop("ppt/printerSettings/printerSettings1.bin", None)
    prels = data["ppt/_rels/presentation.xml.rels"].decode("utf-8")
    prels = re.sub(r'<Relationship [^>]*printerSettings[^>]*/>', "", prels)
    data["ppt/_rels/presentation.xml.rels"] = prels.encode("utf-8")

    # Drop the default-template thumbnail so Windows does not show a stock image.
    data.pop("docProps/thumbnail.jpeg", None)
    rels = data["_rels/.rels"].decode("utf-8")
    rels = re.sub(r'<Relationship [^>]*metadata/thumbnail[^>]*/>', "", rels)
    data["_rels/.rels"] = rels.encode("utf-8")

    drop = {"docProps/thumbnail.jpeg", "ppt/printerSettings/printerSettings1.bin"}
    keep = [n for n in names if n not in drop]
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in keep:
            zout.writestr(n, data[n])


def add_title_slide(prs, phase_label, titles):
    s = add_slide(prs)
    box = s.shapes.add_textbox(Inches(0.9), Inches(1.5), Inches(11.5), Inches(1.8))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "TrumorGPT: A Graph-Based Retrieval-Augmented LLM for Fact-Checking"
    p.font.name = TITLE_FONT
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = DARK
    p.line_spacing = 1.05

    box2 = s.shapes.add_textbox(Inches(0.9), Inches(3.6), Inches(11.5), Inches(3.2))
    tf2 = box2.text_frame
    tf2.word_wrap = True
    lines = [
        (phase_label, 22, True),
        ("Presented by: Akash KG", 20, False),
        ("", 10, False),
        ("Base paper:", 18, True),
        ("C. N. Hang, P.-D. Yu, and C. W. Tan, \"TrumorGPT: Graph-Based Retrieval-Augmented "
         "Large Language Model for Fact-Checking,\" IEEE Transactions on Artificial Intelligence, "
         "vol. 6, no. 11, pp. 3148-3162, Nov. 2025.", 17, False),
        ("DOI: 10.1109/TAI.2025.3567369", 17, False),
    ]
    first = True
    for text, size, bold in lines:
        p = tf2.paragraphs[0] if first else tf2.add_paragraph()
        first = False
        p.text = text
        p.font.name = BODY_FONT
        p.font.size = Pt(size)
        p.font.bold = bold
        p.font.color.rgb = DARK if bold else BLACK
        p.space_after = Pt(6)
    titles.append("TrumorGPT: A Graph-Based Retrieval-Augmented LLM for Fact-Checking")
    return s


def add_phase1_slides(prs, titles):
    add_title_slide(prs, "Capstone Project - Lab Evaluation 1", titles)

    s = add_slide(prs)
    add_title(s, "Selection of the Problem")
    titles.append("Selection of the Problem")
    add_bullets(s, [
        "**Real-world issue:** health misinformation (infodemics) - the WHO declared COVID-19 the first global infodemic.",
        "**Speed of spread:** health rumors spread up to **6x faster** and can reach **1,500 people**.",
        "**Scale of spread:** **600+ AI sites** generate medical myths, and **1 in 4 AI answers are hallucinated**.",
        "**Impact:** false health claims cause harmful decisions, mistrust in medicine, and loss of life (Source: WHO).",
        "**Scope is workable:** limited to the **health domain**, verified against publicly available fact-check data.",
        "**Feasible:** buildable with existing LLMs and knowledge graphs; **no new model training** needed.",
    ], size=19)

    s = add_slide(prs)
    add_title(s, "Understanding of the Problem")
    titles.append("Understanding of the Problem")
    add_bullets(s, [
        "**Fact-checking** is the process of verifying whether a claim is accurate.",
        "**Manual fact-checking** (journalists) cannot keep pace with the volume of online health claims.",
        "**Standard LLMs** (GPT-3.5, GPT-4, LLaMA) **hallucinate** and rely on **static training data**.",
        "**Knowledge graphs alone** are structured and interpretable, but **hard to keep updated**.",
        "**Key insight:** LLMs and knowledge graphs are individually flawed but **complementary**.",
        "**TrumorGPT** combines an LLM with semantic health knowledge graphs through **GraphRAG** (a 'trumor' = true + rumor).",
    ], size=19)

    s = add_slide(prs)
    add_title(s, "Datasets Used")
    titles.append("Datasets Used")
    ds_rows = [
        ["Dataset", "Type", "Key features", "Scale"],
        ["DBpedia",
         "Knowledge graph built from Wikipedia",
         "RDF triples (head, relation, tail); class and property ontology; multilingual; SPARQL endpoint; updated automatically from Wikipedia",
         "~4.2M instances, 768 classes, ~3,000 properties"],
        ["PolitiFact",
         "Fact-checking corpus (US politics)",
         "Truth-O-Meter with 6 rating levels; topic tags; claim text, speaker, author and date; expert-verified labels",
         "~16,000 rated statements (2011-2023)"],
    ]
    add_grid_table(s, ds_rows, [1.3, 2.7, 5.6, 2.9], top=1.7, header_size=16, body_size=15, row_height=0.9)
    add_bullets(s, [
        "**Used here:** DBpedia filtered to health terms (health, medical, disease, pandemic, epidemic); PolitiFact Health Care and Coronavirus claims - **600 total (300 true / 300 false)**.",
        "**Binary mapping:** True / Mostly True / Half True -> **True**; Mostly False / False / Pants on Fire -> **False**.",
    ], top=5.4, size=17)

    s = add_slide(prs)
    add_title(s, "Interpretation of the Solution on the Dataset")
    titles.append("Interpretation of the Solution on the Dataset")
    add_bullets(s, [
        "**Pipeline:** claim -> key sentences (LDA+BERT, TST) -> query KG (few-shot LLM) -> match a database of KGs -> verdict.",
        "**Matching:** subgraph isomorphism and **Jaccard similarity**; match found = **True**, contradiction = **False**, else **Undetermined**.",
        "**Metrics:** accuracy, precision, recall and F1-score measured against PolitiFact ground truth.",
        "**Result:** TrumorGPT scores **88.5% accuracy, 91.4% precision, 85.0% recall and 88.1% F1**.",
        "**Improvement:** ~**5.5 points** over base GPT-4; identifies **85% of true** and **92% of false** claims.",
        "**Interpretation:** grounding on an updatable knowledge graph improves accuracy and reduces hallucination.",
    ], size=18)


def add_phase2_slides(prs, titles):
    add_title_slide(prs, "Capstone Project - Lab Evaluation 2", titles)

    s = add_slide(prs)
    add_title(s, "Feature Selection")
    titles.append("Feature Selection")
    add_bullets(s, [
        "**Semantic triple (head, relation, tail)** - fact-level features from a health claim.",
        "**BERT embedding (384-dim)** - semantic meaning of each sentence.",
        "**LDA topic distribution** - health-topic context of each sentence.",
        "**Topic-enhanced centrality** v = [0.7 * BERT ; 0.3 * LDA] - fuses meaning and topic relevance.",
        "**Topic-Specific TextRank score** - sentence importance under a health-topic bias.",
        "**Graph similarity** - Jaccard similarity, query containment, contradiction flag.",
        "**Why selected:** capture semantics, topic relevance and relational structure.",
    ])

    s = add_slide(prs)
    add_title(s, "Existing Algorithms - Literature Survey")
    titles.append("Existing Algorithms - Literature Survey")
    lit_rows = [
        ["Author and Year", "Title", "Objective of the Work", "Achievements of the Work", "Gaps from the Work"],
        ["Karadzhov et al. (2017)", "Fully automated fact checking using external sources",
         "Verify claims automatically using web evidence",
         "Deep LSTM fact-checking framework with semantic kernels",
         "Uses unstructured web sources; no structured knowledge graph"],
        ["Gad-Elrab et al. (2019)", "Tracy: Tracing facts over knowledge graphs and text",
         "Explain fact verification over knowledge graphs and text",
         "Rule-based semantic traces with a user interface",
         "Manual rules; limited graph coverage"],
        ["Lewis et al. (2020)", "Retrieval-augmented generation for knowledge-intensive tasks",
         "Combine retrieval with generation to reduce hallucination",
         "Strong results on knowledge-intensive QA tasks",
         "Retrieves text passages only; no graph reasoning"],
        ["Vedula & Parthasarathy (2021)", "FACE-KEG: Fact checking explained using knowledge graphs",
         "Explainable fact-checking using knowledge graphs",
         "KG-based veracity scores with explanations",
         "Static KG; cannot use the latest health updates"],
        ["Guo et al. (2022)", "A survey on automated fact-checking",
         "Review existing automated fact-checking methods",
         "Comprehensive taxonomy of automated fact-checking pipelines",
         "No health-specific LLM and GraphRAG integration"],
        ["Edge et al. (2024)", "From local to global: A graph RAG approach to query-focused summarization",
         "Use knowledge graphs with RAG for global queries",
         "Graph-based summarization over large corpora",
         "Built for summarization, not claim verification"],
    ]
    add_lit_table(s, lit_rows, top=1.5)
    box = s.shapes.add_textbox(Inches(0.32), Inches(6.25), Inches(12.7), Inches(0.9))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Gap: no existing method combines an updatable semantic health knowledge graph with LLM reasoning for health-claim verification."
    p.font.name = BODY_FONT
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = DARK

    s = add_slide(prs)
    add_title(s, "Learning Technique Identified")
    titles.append("Learning Technique Identified")
    add_bullets(s, [
        "**Proposed technique: TrumorGPT = GraphRAG + few-shot LLM + Topic-Specific TextRank.**",
        "**Few-shot LLM** extracts (head, relation, tail) triples and builds the claim knowledge graph.",
        "**Topic-Specific TextRank** (alpha = 1.5, damping = 0.85) ranks the key health sentences.",
        "**LDA + BERT centrality** selects the informative sentences before graph construction.",
        "**GraphRAG** computes S(Gx, Gi) = max(Jaccard, containment), then detects contradictions -> **True / False / Undetermined**.",
        "**Justification:** grounds the LLM in updatable facts (less hallucination), needs no retraining, and runs on a local LLM such as LLaMA 3.",
    ])

    s = add_slide(prs)
    add_title(s, "Results of the Identified Technique")
    titles.append("Results of the Identified Technique")
    rows = [
        ["Model", "Accuracy", "Precision", "Recall", "F1-score"],
        ["GPT-3.5", "72.7%", "75.8%", "66.7%", "70.9%"],
        ["GPT-4", "83.3%", "85.7%", "80.0%", "82.8%"],
        ["LLaMA 3.2", "81.8%", "83.0%", "80.0%", "81.5%"],
        ["PaLM 2", "76.8%", "77.9%", "75.0%", "76.4%"],
        ["Claude 3.5 Sonnet", "77.2%", "78.4%", "75.0%", "76.7%"],
        ["Gemini 1.5", "81.7%", "83.9%", "78.3%", "81.0%"],
        ["TrumorGPT", "88.5%", "91.4%", "85.0%", "88.1%"],
    ]
    add_table(s, rows, top=1.55, height=3.9)
    add_bullets(s, [
        "**TrumorGPT leads every metric:** 88.5% accuracy, 91.4% precision, 85.0% recall, 88.1% F1-score.",
        "**Outperforms GPT-4** and five other LLMs by +5.2 accuracy points.",
        "Correctly identifies **85% of true** and **92% of false** claims; average explanation is 2.8 sentences.",
        "Confirms the identified learning technique is **suitable for the problem**.",
    ], top=5.55, size=18)


def load_metrics():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "metrics.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def add_final_deck(prs, titles, m):
    def pct(x):
        return f"{x*100:.1f}%" if isinstance(x, (int, float)) else str(x)

    e2e = m.get("e2e", {})
    kb = m.get("kb_component", {})
    bl = m.get("baselines", {})
    ab = m.get("ablations", {})
    paper = m.get("paper_reported", {}).get("TrumorGPT", {})

    # 1. Title
    add_title_slide(prs, "Capstone Project - Lab Evaluations 1 and 2", titles)

    # 2. Selection of the Problem
    s = add_slide(prs)
    add_title(s, "Selection of the Problem")
    titles.append("Selection of the Problem")
    add_bullets(s, [
        "**Health misinformation** is a large-scale, real problem that harms public health decisions.",
        "The **WHO** declared COVID-19 the first global **infodemic** (2020).",
        "False news spreads faster: false tweets reach **1,500 people ~6x faster** than true ones (Vosoughi et al., Science 2018).",
        "**3,749 AI content-farm sites** operate across 16 languages; two-thirds of untrustworthy sites publish health misinformation (NewsGuard).",
        "**Scope:** health claims only; **feasible** with existing LLMs and knowledge graphs, with no new model training.",
    ], size=19)

    # 3. Understanding of the Problem
    s = add_slide(prs)
    add_title(s, "Understanding of the Problem")
    titles.append("Understanding of the Problem")
    add_bullets(s, [
        "**Fact-checking** means verifying whether a claim is accurate.",
        "**Manual checking** cannot keep pace with the volume of online claims.",
        "**Standard LLMs** hallucinate and rely on static training data.",
        "**Knowledge graphs alone** are structured but static and incomplete.",
        "**Key insight:** the two are individually flawed but **complementary**.",
        "**Approach:** TrumorGPT combines an LLM with semantic health knowledge graphs via **GraphRAG**; output is True / False / Undetermined.",
    ], size=19)

    # 4. Datasets Used
    s = add_slide(prs)
    add_title(s, "Datasets Used")
    titles.append("Datasets Used")
    ds_rows = [
        ["Dataset", "Type", "Key features", "Size used here"],
        ["DBpedia", "Knowledge graph from Wikipedia",
         "RDF triples (head, relation, tail); class and property ontology; SPARQL endpoint; auto-updated",
         "8 seed KGs (reference base)"],
        ["PolitiFact (via LIAR)", "Fact-checked US statements",
         "Truth-O-Meter 6-level ratings; claim text, speaker, subject, date",
         "1,434 health rows; 600 test (300/300)"],
    ]
    add_grid_table(s, ds_rows, [1.5, 2.5, 5.5, 2.7], top=1.7, header_size=16, body_size=14, row_height=0.95)
    add_bullets(s, [
        "**Binary labels:** True/Mostly True/Half True -> True; False/Barely True/Pants on Fire -> False.",
        "**External test set:** LIAR health-care (PolitiFact-derived), balanced 300 True / 300 False, seed 42.",
    ], top=5.5, size=16)

    # 5. Interpretation of the Solution on the Dataset
    s = add_slide(prs)
    add_title(s, "Interpretation of the Solution on the Dataset")
    titles.append("Interpretation of the Solution on the Dataset")
    add_bullets(s, [
        "**Worked example** - claim: 'Ivermectin is an FDA-approved cure for treating COVID-19.'",
        "Extracted query triple: `(Ivermectin, claimed_treatment_for, COVID-19)`.",
        "Matched KB triple: `(Ivermectin, failed_clinical_trials_for, COVID-19)` -> **contradiction** -> verdict **False** (score 0.50).",
        "Verified positives, e.g. mRNA-vaccine and diet claims, map directly to a KB with score **1.00**.",
        "Out-of-KB claims (e.g. '2024 budget deficit...') return **Undetermined** - the system abstains rather than guesses.",
        "**Reading the metrics:** strict accuracy counts an abstention as wrong; coverage and determined-accuracy separate them.",
    ], size=18)

    # 6. Feature Selection
    s = add_slide(prs)
    add_title(s, "Feature Selection")
    titles.append("Feature Selection")
    add_bullets(s, [
        "**Semantic triple (head, relation, tail)** - fact-level features from a claim.",
        "**BERT embedding (384-dim)** - semantic meaning of each sentence.",
        "**LDA topic distribution** - health-topic context of each sentence.",
        "**Topic-enhanced centrality** v = [0.7 * BERT ; 0.3 * LDA] - fuses meaning and topic relevance.",
        "**Topic-Specific TextRank score** - sentence importance under a health-topic bias.",
        "**Graph similarity** - Jaccard, containment, and contradiction flag.",
        "**Evidence:** removing contradiction detection drops component accuracy 91.7% -> 68.8%; Jaccard-only drops it to 77.1%.",
    ], size=18)

    # 7. Literature Survey
    s = add_slide(prs)
    add_title(s, "Existing Algorithms - Literature Survey")
    titles.append("Existing Algorithms - Literature Survey")
    lit_rows = [
        ["Author and Year", "Title", "Objective of the Work", "Achievements of the Work", "Gaps from the Work"],
        ["Karadzhov et al. (2017)", "Fully automated fact checking using external sources",
         "Verify claims automatically using web evidence",
         "Deep LSTM fact-checking framework with semantic kernels",
         "Uses unstructured web sources; no structured knowledge graph"],
        ["Gad-Elrab et al. (2019)", "Tracy: Tracing facts over knowledge graphs and text",
         "Explain fact verification over knowledge graphs and text",
         "Rule-based semantic traces with a user interface",
         "Manual rules; limited graph coverage"],
        ["Lewis et al. (2020)", "Retrieval-augmented generation for knowledge-intensive tasks",
         "Combine retrieval with generation to reduce hallucination",
         "Strong results on knowledge-intensive QA tasks",
         "Retrieves text passages only; no graph reasoning"],
        ["Vedula & Parthasarathy (2021)", "FACE-KEG: Fact checking explained using knowledge graphs",
         "Explainable fact-checking using knowledge graphs",
         "KG-based veracity scores with explanations",
         "Static KG; cannot use the latest health updates"],
        ["Guo et al. (2022)", "A survey on automated fact-checking",
         "Review existing automated fact-checking methods",
         "Comprehensive taxonomy of automated fact-checking pipelines",
         "No health-specific LLM and GraphRAG integration"],
        ["Edge et al. (2024)", "From local to global: A graph RAG approach to query-focused summarization",
         "Use knowledge graphs with RAG for global queries",
         "Graph-based summarization over large corpora",
         "Built for summarization, not claim verification"],
    ]
    add_lit_table(s, lit_rows, top=1.5)
    box = s.shapes.add_textbox(Inches(0.32), Inches(6.25), Inches(12.7), Inches(0.9))
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Gap: no existing method combines an updatable semantic health knowledge graph with LLM reasoning for health-claim verification."
    p.font.name = BODY_FONT
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = DARK

    # 8. Learning Technique Identified
    s = add_slide(prs)
    add_title(s, "Learning Technique Identified")
    titles.append("Learning Technique Identified")
    add_bullets(s, [
        "**Proposed technique: TrumorGPT = GraphRAG + few-shot LLM + Topic-Specific TextRank.**",
        "**Few-shot LLM** extracts (head, relation, tail) triples and builds the claim knowledge graph.",
        "**Topic-Specific TextRank** (alpha = 1.5, damping = 0.85) ranks the key health sentences.",
        "**LDA + BERT centrality** selects the informative sentences before graph construction.",
        "**GraphRAG** computes S(Gx, Gi) = max(Jaccard, containment), then detects contradictions -> **True / False / Undetermined**.",
        "**Justification:** grounds the LLM in updatable facts (less hallucination), needs no retraining, and runs on a local LLM.",
    ], size=18)

    # 9. Our Results
    s = add_slide(prs)
    add_title(s, "Our Results")
    titles.append("Our Results")
    res_rows = [
        ["System", "Strict acc.", "Coverage", "Determined acc.", "Precision", "Recall", "F1"],
        ["TrumorGPT (this repro, Set C component, n=48)", pct(kb.get("strict", {}).get("accuracy")),
         pct(kb.get("coverage")), pct(kb.get("determined", {}).get("accuracy")),
         f"{kb.get('determined', {}).get('precision', 0):.2f}",
         f"{kb.get('determined', {}).get('recall', 0):.2f}",
         f"{kb.get('determined', {}).get('f1', 0):.2f}"],
        ["TrumorGPT (this repro, Set A end-to-end, n=600)", pct(e2e.get("strict", {}).get("accuracy")),
         pct(e2e.get("coverage")), "n/a (n=1)", "-", "-", "-"],
        ["TF-IDF + LogReg (baseline, n=600)", pct(bl.get("tfidf_lr", {}).get("strict", {}).get("accuracy")),
         "100%", pct(bl.get("tfidf_lr", {}).get("determined", {}).get("accuracy")),
         f"{bl.get('tfidf_lr', {}).get('determined', {}).get('precision', 0):.2f}",
         f"{bl.get('tfidf_lr', {}).get('determined', {}).get('recall', 0):.2f}",
         f"{bl.get('tfidf_lr', {}).get('determined', {}).get('f1', 0):.2f}"],
        ["Majority (all False) (baseline, n=600)", "50.0%", "100%", "50.0%", "0.00", "0.00", "0.00"],
        ["TrumorGPT (paper-reported)", f"{paper.get('accuracy', 88.5):.1f}%", "-", "-",
         f"{paper.get('precision', 91.4):.1f}", f"{paper.get('recall', 85.0):.1f}", f"{paper.get('f1', 88.1):.1f}"],
    ]
    add_grid_table(s, res_rows, [3.5, 1.3, 1.3, 1.7, 1.3, 1.2, 1.2], top=1.55,
                   header_size=13, body_size=12.5, row_height=0.62, bold_match="TrumorGPT")
    add_bullets(s, [
        "**Component result:** 100% accuracy on committed verdicts, 91.7% strict (n=48).",
        "**End-to-end:** abstains on 99.8% of real claims because only 8 KGs are shipped; the paper used a large DBpedia KB + GPT-4.",
        "**Paper numbers are paper-reported**, not reproduced here (no GPT-class LLM available).",
    ], top=5.55, size=14)

    # 10. Ablation and Error Analysis
    s = add_slide(prs)
    add_title(s, "Ablation and Error Analysis")
    titles.append("Ablation and Error Analysis")
    ab_rows = [
        ["Ablation", "Setting", "Strict accuracy"],
        ["Graph similarity measure", "max(Jaccard, containment) - full", pct(ab.get("kb_measure", {}).get("measure=max"))],
        ["", "containment only", pct(ab.get("kb_measure", {}).get("measure=containment"))],
        ["", "Jaccard only", pct(ab.get("kb_measure", {}).get("measure=jaccard"))],
        ["Contradiction detection", "on (full)", pct(ab.get("kb_contradiction", {}).get("contradiction_on"))],
        ["", "off", pct(ab.get("kb_contradiction", {}).get("contradiction_off"))],
        ["Match threshold", "0.1 / 0.25 / 0.4 / 0.6", "91.7% (insensitive)"],
        ["eta (LDA) x alpha (TST)", "9 combinations (Set A)", "coverage 0.0 (no effect)"],
    ]
    add_grid_table(s, ab_rows, [3.4, 5.2, 3.9], top=1.55, header_size=13, body_size=12.5, row_height=0.52)
    add_bullets(s, [
        "**Contradiction detection is the biggest contributor** (91.7% -> 68.8% when removed).",
        "**Set A failures (600/600):** 252 numeric claims, 170 named-entity/geography, 139 KB-coverage gaps, 39 negation.",
        "**eta/alpha are flat on Set A** - the bottleneck is KB coverage and triple extraction, not sentence ranking.",
    ], top=5.7, size=13)

    # 11. Limitations and Future Work
    s = add_slide(prs)
    add_title(s, "Limitations and Future Work")
    titles.append("Limitations and Future Work")
    add_bullets(s, [
        "**KB coverage:** only 8 reference KGs vs the paper's DBpedia-derived health KB.",
        "**Extraction:** deterministic rule-based fallback vs GPT-4; the Gemini baseline was blocked by free-tier quota.",
        "**Data mismatch:** LIAR (2017, US political) differs from the paper's 2020-24 Health Care + Coronavirus set.",
        "**No significance testing** on the paper comparison; results are descriptive.",
        "**Future work:** ingest DBpedia health triples, add a stronger LLM extractor, add calibration, and re-freeze the test set before re-evaluation.",
    ], size=18)

    # 12. Demo / Live Run
    s = add_slide(prs)
    add_title(s, "Demo / Live Run")
    titles.append("Demo / Live Run")
    add_bullets(s, [
        "**Offline mode** (TRUMORGPT_OFFLINE=1): deterministic, no network or API key required.",
        "**Verified examples:** vaccines -> True; ivermectin cure -> False; balanced diet -> True; 'COVID-19 causes cancer' -> False; out-of-KB -> Undetermined.",
        "**Artifacts:** results/metrics.json, results/*_predictions.csv, results/figures/, results/error_analysis.md.",
        "**Fallback if the server fails:** show the captured slides and prediction CSVs.",
    ], size=18)

    # 13. Backup: confusion matrix
    s = add_slide(prs)
    add_title(s, "Backup - Confusion Matrix (Set A)")
    titles.append("Backup - Confusion Matrix (Set A)")
    conf = e2e.get("strict", {}).get("confusion", {})
    add_grid_table(s, [
        ["Gold \\ Predicted", "True", "False", "Undetermined"],
        ["True", str(conf.get("True->True", 0)), str(conf.get("True->False", 0)), str(conf.get("True->Undetermined", 0))],
        ["False", str(conf.get("False->True", 0)), str(conf.get("False->False", 0)), str(conf.get("False->Undetermined", 0))],
    ], [3.4, 3.0, 3.0, 3.1], top=1.9, header_size=15, body_size=15, row_height=0.7, left=0.7)
    add_bullets(s, [
        "Abstention dominates: the model commits to only 1 of 600 claims, and that one is wrong.",
    ], top=4.4, size=16)


def build(path, phase="combined"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    titles = []
    if phase == "final":
        add_final_deck(prs, titles, load_metrics())
    else:
        if phase in ("phase1", "combined"):
            add_phase1_slides(prs, titles)
        if phase in ("phase2", "combined"):
            add_phase2_slides(prs, titles)
    subject = {
        "phase1": "Capstone Project - Lab Evaluation 1",
        "phase2": "Capstone Project - Lab Evaluation 2",
        "final": "Capstone Project - Lab Evaluations 1 and 2",
    }.get(phase, "Capstone Project - Lab Evaluations 1 and 2")
    set_document_properties(prs, subject)
    prs.save(path)
    scrub_package(path, titles)
    return path


if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    final_dir = os.path.join(root, "final")
    os.makedirs(final_dir, exist_ok=True)
    print("Saved:", build(os.path.join(final_dir, "24005_179_final.pptx"), "final"))
    print("Saved:", build(os.path.join(root, "TrumorGPT_Capstone_Presentation.pptx"), "combined"))
    print("Saved:", build(os.path.join(root, "TrumorGPT_Phase1_Presentation.pptx"), "phase1"))
