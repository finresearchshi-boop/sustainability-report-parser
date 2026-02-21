from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

import pandas as pd

from .models import Node, Section
from .pdf_extract import extract_pages_text, extract_outline
from .toc_detect import find_toc_pages, parse_toc_entries_from_pages
from .segment import detect_headings
from .section_tree import build_tree_from_entries, finalize_tree, flatten_sections, tree_to_markdown
from .export import write_raw_text, write_tree_json, write_tree_md, write_sections_jsonl
from .assets import extract_figures, extract_tables


@dataclass
class ParseResult:
    pdf_path: str
    strategy_used: str
    page_count: int
    tree: Node
    sections: List[Section]
    tree_md: str

    figures_df: Optional[pd.DataFrame] = None
    tables_df: Optional[pd.DataFrame] = None

    def sections_df(self) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        for s in self.sections:
            rows.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "level": s.level,
                    "start_page": s.start_page,
                    "end_page": s.end_page,
                    "path": " > ".join(s.path),
                    "text": s.text,
                    "n_chars": len(s.text),
                    "n_words": len(s.text.split()),
                }
            )
        return pd.DataFrame(rows)

    def export(self, out_dir: str) -> None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        pages_text = extract_pages_text(self.pdf_path)
        write_raw_text(str(out), pages_text)
        write_tree_json(str(out), self.tree)
        write_tree_md(str(out), self.tree_md)
        write_sections_jsonl(str(out), self.sections)

    def export_assets(
        self,
        out_dir: str,
        export_figures: bool = True,
        export_tables: bool = True,
        table_max_pages: Optional[int] = None,
    ) -> "ParseResult":
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)

        if export_figures:
            self.figures_df = extract_figures(self.pdf_path, str(out / "figures"))

        if export_tables:
            self.tables_df = extract_tables(
                self.pdf_path, str(out / "tables"), max_pages=table_max_pages
            )

        return self


def parse_pdf(
    pdf_path: str,
    strategy: str = "auto",
    max_toc_pages: int = 10,
) -> ParseResult:
    pages_text = extract_pages_text(pdf_path)
    doc_pages = len(pages_text)

    entries: Optional[List[Tuple[int, str, int]]] = None
    used = "none"

    if strategy in ("auto", "outline"):
        toc = extract_outline(pdf_path)
        if toc:
            entries = toc
            used = "outline"

    if entries is None and strategy in ("auto", "toc"):
        toc_pages = find_toc_pages(pages_text, max_pages=max_toc_pages)
        if toc_pages:
            toc_entries = parse_toc_entries_from_pages(pages_text, toc_pages)
            if toc_entries:
                entries = toc_entries
                used = "toc"

    if entries is None and strategy in ("auto", "headings"):
        headings = detect_headings(pages_text)
        if headings:
            entries = headings
            used = "headings"

    if not entries:
        raise ValueError(
            "No outline/TOC/headings detected. Try a different PDF or extend heuristics."
        )

    root = build_tree_from_entries(entries)
    root = finalize_tree(root, doc_pages)
    sections = flatten_sections(root, pages_text)
    md = tree_to_markdown(root)

    return ParseResult(
        pdf_path=pdf_path,
        strategy_used=used,
        page_count=doc_pages,
        tree=root,
        sections=sections,
        tree_md=md,
    )
