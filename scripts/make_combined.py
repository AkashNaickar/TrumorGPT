"""Combines the Phase 1+2 deck with the Review-3 deck into a single 24005_179.pptx."""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_ppt as B
import make_review3 as R
from pptx import Presentation
from pptx.util import Inches

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
OUT = os.path.join(ROOT, "24005_179.pptx")
BACKUP = os.path.join(ROOT, "24005_179_phase12_backup.pptx")


def build():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    titles = []

    B.add_phase1_slides(prs, titles)     # Lab Evaluation 1 (5 slides)
    B.add_phase2_slides(prs, titles)     # Lab Evaluation 2 (5 slides)
    R.add_review3_slides(prs, titles)    # Review 3 (7 slides)

    if os.path.exists(OUT):
        shutil.copy2(OUT, BACKUP)

    B.set_document_properties(prs, "Capstone Project - Lab Evaluations 1 and 2 + Review 3")
    prs.save(OUT)
    B.scrub_package(OUT, titles)
    print("Saved:", OUT, "slides:", len(prs.slides))
    print("Backup of previous file:", BACKUP)


if __name__ == "__main__":
    build()
