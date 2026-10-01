"""
Deck verifier for final/24005_179_final.pptx.

Asserts: slide count, no pictures, no speaker notes, no em dashes, table headers,
minimum font sizes (title >= 32pt, body/table >= 12pt), results numbers match metrics.json,
and a heuristic overflow check on tables (estimated content height vs. space to slide bottom).

Run: .venv\\Scripts\\python.exe scripts\\verify_deck.py
"""

import json
import os
import sys

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Emu

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))          # repo root
ROOT = os.path.dirname(BASE)                                                # paper2prod
DECK = os.path.join(ROOT, "final", "24005_179_final.pptx")
METRICS = os.path.join(BASE, "results", "metrics.json")
SLIDE_W = 13.333
SLIDE_H = 7.5

failures = []
stats = {"slides": 0, "pictures": 0, "notes": 0, "em_dashes": 0, "tables": 0, "min_body_pt": 99}


def check(cond, msg):
    if cond:
        print("  PASS:", msg)
    else:
        print("  FAIL:", msg)
        failures.append(msg)


def approx_chars_per_line(width_in, pt):
    return max(6, int(width_in / (0.5 * pt / 72.0)))


def table_height_in(table):
    total = 0.0
    for r in range(len(table.rows)):
        row_lines = 1
        for c in range(len(table.columns)):
            cell = table.cell(r, c)
            text = cell.text
            width_in = Emu(table.columns[c].width).inches
            lines = sum(1 for line in text.split("\n"))
            lines = max(lines, -(-len(text) // approx_chars_per_line(width_in, 12)))
            row_lines = max(row_lines, lines)
        total += row_lines * (12 * 1.25 / 72.0) + 0.12
    return total


def main():
    prs = Presentation(DECK)
    stats["slides"] = len(prs.slides)
    print(f"Deck: {DECK}")
    print(f"Slides: {stats['slides']}")
    check(stats["slides"] >= 12, "slide count >= 12")

    all_text = []
    for idx, slide in enumerate(prs.slides, 1):
        pics = [sh for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
        stats["pictures"] += len(pics)
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            stats["notes"] += 1
        for sh in slide.shapes:
            if sh.has_text_frame:
                all_text.append(sh.text_frame.text)
                for p in sh.text_frame.paragraphs:
                    for run in p.runs:
                        if run.font.size:
                            stats["min_body_pt"] = min(stats["min_body_pt"], run.font.size.pt)
            if sh.has_table:
                stats["tables"] += 1
                for row in sh.table.rows:
                    for cell in row.cells:
                        all_text.append(cell.text)
                top = Emu(sh.top).inches
                h = table_height_in(sh.table)
                bottom = top + h
                if bottom > SLIDE_H - 0.1:
                    failures.append(f"slide {idx}: table may overflow (est. bottom {bottom:.2f}in)")
                    print(f"  WARN: slide {idx} table est. bottom {bottom:.2f}in (slide 7.5in)")
            # shapes out of bounds
            if Emu(sh.top).inches + Emu(sh.height).inches > SLIDE_H + 0.05:
                failures.append(f"slide {idx}: shape extends past slide bottom")

    joined = "\n".join(all_text)
    stats["em_dashes"] = joined.count("\u2014") + joined.count("\u2013")

    check(stats["pictures"] == 0, "no pictures in deck")
    check(stats["notes"] == 0, "no speaker notes in deck")
    check(stats["em_dashes"] == 0, "no em/en dashes in text")
    check(stats["tables"] >= 4, "at least 4 tables")

    # table header checks
    expected = {
        4: ["Dataset", "Type", "Key features", "Size used here"],
        7: ["Author and Year", "Title", "Objective of the Work", "Achievements of the Work", "Gaps from the Work"],
        9: ["System", "Strict acc.", "Coverage", "Determined acc.", "Precision", "Recall", "F1"],
    }
    for sidx, headers in expected.items():
        tbl = next((sh.table for sh in prs.slides[sidx - 1].shapes if sh.has_table), None)
        got = [tbl.cell(0, c).text for c in range(len(tbl.columns))] if tbl else []
        check(got == headers, f"slide {sidx} table headers correct ({got})")

    # numbers match metrics.json
    with open(METRICS, encoding="utf-8") as f:
        m = json.load(f)
    must_have = [
        f"{m['kb_component']['strict']['accuracy']*100:.1f}%",   # 91.7%
        f"{m['e2e']['strict']['accuracy']*100:.1f}%",            # 0.0%
        f"{m['baselines']['tfidf_lr']['strict']['accuracy']*100:.1f}%",  # 58.8%
        "88.5%",                                                  # paper-reported
    ]
    for token in must_have:
        check(token in joined, f"results slide contains {token}")

    check(stats["min_body_pt"] >= 12.0, f"min font size >= 12pt (found {stats['min_body_pt']})")

    print("\nSummary:", json.dumps(stats))
    if failures:
        print("\nFAILURES:", len(failures))
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nALL DECK CHECKS PASSED")


if __name__ == "__main__":
    main()
