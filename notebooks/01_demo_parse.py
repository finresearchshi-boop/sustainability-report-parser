# Demo: parse a PDF and show the outline
# Run from repo root:
#   python notebooks/01_demo_parse.py data/pdfs/your_report.pdf

import sys
from pathlib import Path
import json

from sustain_parser.cli import parse

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notebooks/01_demo_parse.py data/pdfs/your_report.pdf")
        raise SystemExit(1)
    pdf = sys.argv[1]
    out = "outputs/demo"
    parse(pdf_path=pdf, out=out, strategy="auto")

    print("\nTree markdown at:", Path(out) / "tree.md")
