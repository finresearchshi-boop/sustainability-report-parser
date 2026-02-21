from __future__ import annotations

import os
from typing import Optional, List, Tuple

import typer
from rich.console import Console
from rich.table import Table

from .pdf_extract import extract_pages_text, extract_outline
from .toc_detect import find_toc_pages, parse_toc_entries_from_pages
from .segment import detect_headings
from .section_tree import build_tree_from_entries, finalize_tree, flatten_sections, tree_to_markdown
from .export import write_raw_text, write_tree_json, write_tree_md, write_sections_jsonl

app = typer.Typer(add_completion=False)
console = Console()


def _summarize_entries(entries: List[Tuple[int, str, int]], max_rows: int = 12) -> None:
    t = Table(title="Detected outline entries (preview)")
    t.add_column("Level", justify="right")
    t.add_column("Title")
    t.add_column("Page", justify="right")

    for lvl, title, page in entries[:max_rows]:
        t.add_row(str(lvl), title, str(page))
    if len(entries) > max_rows:
        t.add_row("…", f"(+{len(entries) - max_rows} more)", "…")
    console.print(t)


@app.command()
def parse(
    pdf_path: str = typer.Argument(..., help="Path to a sustainability report PDF"),
    out: str = typer.Option("outputs/report", "--out", help="Output directory"),
    strategy: str = typer.Option("auto", "--strategy", help="auto|outline|toc|headings"),
    max_toc_pages: int = typer.Option(8, "--max-toc-pages", help="Search TOC within first N pages"),
):
    """
    Parse a PDF into a topic tree + per-section text exports.
    """
    if not os.path.exists(pdf_path):
        raise typer.BadParameter(f"PDF not found: {pdf_path}")

    console.print(f"[bold]Reading PDF:[/bold] {pdf_path}")
    pages_text = extract_pages_text(pdf_path)
    doc_pages = len(pages_text)
    console.print(f"[green]Extracted[/green] {doc_pages} pages of text.")

    entries: Optional[List[Tuple[int, str, int]]] = None
    used = None

    if strategy in ("auto", "outline"):
        toc = extract_outline(pdf_path)
        if toc:
            entries = toc
            used = "outline"
            console.print("[green]Using PDF outline/bookmarks.[/green]")

    if entries is None and strategy in ("auto", "toc"):
        toc_pages = find_toc_pages(pages_text, max_pages=max_toc_pages)
        if toc_pages:
            toc_entries = parse_toc_entries_from_pages(pages_text, toc_pages)
            if toc_entries:
                entries = toc_entries
                used = "toc"
                console.print(f"[green]Using TOC pages[/green] at indices {toc_pages} (0-based).")

    if entries is None and strategy in ("auto", "headings"):
        headings = detect_headings(pages_text)
        if headings:
            entries = headings
            used = "headings"
            console.print("[yellow]Using fallback heading detection.[/yellow]")

    if not entries:
        console.print("[red]No entries found.[/red] Try a different PDF or extend heuristics.")
        raise typer.Exit(code=2)

    _summarize_entries(entries)

    # Build + finalize tree
    root = build_tree_from_entries(entries)
    root = finalize_tree(root, doc_pages)

    # Flatten to sections
    sections = flatten_sections(root, pages_text)
    console.print(f"[bold]Sections produced:[/bold] {len(sections)} (strategy={used})")

    # Export
    write_raw_text(out, pages_text)
    write_tree_json(out, root)
    md = tree_to_markdown(root)
    write_tree_md(out, md)
    write_sections_jsonl(out, sections)

    console.print(f"[green]Done.[/green] Outputs written to: {out}")
    console.print("Open [bold]tree.md[/bold] to see the outline.")


if __name__ == "__main__":
    app()
