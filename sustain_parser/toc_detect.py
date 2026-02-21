from __future__ import annotations

from typing import List, Optional, Tuple, Dict
import re


TOC_KEYWORDS = [
    "table of contents",
    "contents",
]


def _looks_like_toc_line(line: str) -> bool:
    """
    Heuristic: 'Section title ....... 12' or '2.3 Climate Risk 45'
    """
    s = line.strip()
    if len(s) < 6:
        return False
    # Must contain a page number at end
    if not re.search(r"\b(\d{1,4})\s*$", s):
        return False
    # Must have some letters
    if not re.search(r"[A-Za-z]", s):
        return False
    # dot leaders OR lots of spaces between title and page
    if "..." in s or re.search(r"\s{3,}\d{1,4}\s*$", s):
        return True
    # also allow "1.2 Something 12"
    if re.match(r"^(\d+(\.\d+){0,4}|[A-Z])[\.\)]?\s+\S+", s):
        return True
    return False


def find_toc_pages(pages_text: List[str], max_pages: int = 8) -> List[int]:
    """
    Find likely TOC pages near the front of the document.
    Returns page indices (0-based).
    """
    candidates = []
    n = min(len(pages_text), max_pages)
    for i in range(n):
        low = pages_text[i].lower()
        if any(k in low for k in TOC_KEYWORDS):
            candidates.append(i)
    return candidates


def parse_toc_entries_from_pages(pages_text: List[str], toc_pages: List[int]) -> List[Tuple[int, str, int]]:
    """
    Parse TOC-like lines and infer (level, title, start_page_1_indexed).
    Level inference uses numbering depth: 1 -> level 1, 1.2 -> level 2, etc.
    If no numbering, use a default level 1.
    """
    entries: List[Tuple[int, str, int]] = []
    seen = set()

    for p in toc_pages:
        lines = [ln.strip() for ln in pages_text[p].splitlines()]
        for ln in lines:
            if not _looks_like_toc_line(ln):
                continue
            # Extract trailing page number
            m = re.search(r"\b(\d{1,4})\s*$", ln)
            if not m:
                continue
            page = int(m.group(1))
            title_part = ln[: m.start()].rstrip(". ").strip()
            title_part = re.sub(r"\.{2,}$", "", title_part).strip()

            # Try to split leading numbering like "2.3" or "A"
            mnum = re.match(r"^(\d+(?:\.\d+){0,6}|[A-Z])[\.\)]?\s+(.*)$", title_part)
            if mnum:
                num = mnum.group(1)
                title = mnum.group(2).strip()
                if re.match(r"^\d", num):
                    level = num.count(".") + 1
                else:
                    level = 1
            else:
                title = title_part
                level = 1

            key = (level, title.lower(), page)
            if key in seen:
                continue
            seen.add(key)
            entries.append((level, title, page))

    # Sort by page then level
    entries.sort(key=lambda x: (x[2], x[0], x[1]))
    return entries
