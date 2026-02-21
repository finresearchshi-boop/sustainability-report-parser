from __future__ import annotations

from typing import List, Tuple, Optional
import re


def detect_headings(pages_text: List[str]) -> List[Tuple[int, str, int]]:
    """
    Fallback heading detection directly from body text.
    Returns list of (level, title, page_1_indexed).

    This is intentionally conservative to avoid false positives.
    """
    headings: List[Tuple[int, str, int]] = []
    seen = set()

    # Only scan first ~90% of pages; appendices can be noisy but still relevant.
    for i, txt in enumerate(pages_text):
        page_no = i + 1
        lines = [ln.strip() for ln in txt.splitlines()]
        for ln in lines:
            s = re.sub(r"\s+", " ", ln).strip()
            if len(s) < 6 or len(s) > 120:
                continue

            # Strong pattern: numbered headings "1", "1.1", "2.3.4"
            m = re.match(r"^(\d+(?:\.\d+){0,5})\s+([A-Z][A-Za-z0-9&,\-:’'()/ ]+)$", s)
            if m:
                num = m.group(1)
                title = m.group(2).strip()
                level = num.count(".") + 1
                key = (level, title.lower(), page_no)
                if key not in seen:
                    headings.append((level, title, page_no))
                    seen.add(key)
                continue

            # Title-like: ALL CAPS short lines (common in reports)
            if s.isupper() and 6 <= len(s) <= 60 and re.search(r"[A-Z]", s):
                title = s.title()
                level = 1
                key = (level, title.lower(), page_no)
                if key not in seen:
                    headings.append((level, title, page_no))
                    seen.add(key)
                continue

            # "Materiality assessment", "Governance", etc: Title Case / Proper case
            # Require no trailing period and must have >=2 words
            if s.endswith("."):
                continue
            if len(s.split()) >= 2 and re.match(r"^[A-Z][A-Za-z0-9&,\-:’'()/ ]+$", s):
                # Avoid capturing sentences by requiring low punctuation density
                if sum(ch in ",;:" for ch in s) > 2:
                    continue
                # Avoid lines that look like captions (e.g., "Figure 1:")
                if re.match(r"^(figure|table)\s+\d+", s.lower()):
                    continue
                # Level unknown => assume 2 if line is indented in source (we can't see indent here),
                # keep as level 1 for simplicity.
                level = 1
                title = s
                key = (level, title.lower(), page_no)
                if key not in seen:
                    headings.append((level, title, page_no))
                    seen.add(key)

    # De-duplicate and sort
    headings.sort(key=lambda x: (x[2], x[0], x[1]))
    return headings
