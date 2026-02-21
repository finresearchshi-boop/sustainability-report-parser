from __future__ import annotations

from typing import List, Tuple, Optional
import re

import fitz  # PyMuPDF


def extract_pages_text(pdf_path: str) -> List[str]:
    """Extract text per page (0-index pages)."""
    doc = fitz.open(pdf_path)
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        # "text" is generally best for linear text; "blocks" can help but is noisier.
        txt = page.get_text("text") or ""
        # Normalize whitespace a bit
        txt = re.sub(r"\u00a0", " ", txt)
        txt = re.sub(r"[ \t]+\n", "\n", txt)
        pages.append(txt)
    return pages


def extract_outline(pdf_path: str) -> Optional[List[Tuple[int, str, int]]]:
    """
    Return PDF outline/bookmarks if present.

    Output format matches PyMuPDF get_toc():
        (level, title, page_number_1_indexed)

    Returns None if empty.
    """
    doc = fitz.open(pdf_path)
    toc = doc.get_toc(simple=True)  # list of [lvl, title, page]
    if not toc:
        return None
    # Ensure tuples
    return [(int(lvl), str(title).strip(), int(page)) for (lvl, title, page) in toc]
