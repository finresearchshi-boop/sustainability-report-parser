# Sustainability Report Parser (Teaching Repo)

A small, classroom-friendly Python project to parse a company's sustainability report PDF and produce a **tree of sections** (topic outline) plus **per-section text** for analysis.

This is inspired by SEC parsing projects (e.g., `sec-parser`), but tailored to sustainability reports (Materiality, Governance, Climate, Metrics & Targets, Assurance, etc.).

## What it does

Given a PDF, the parser tries (in order):

1. **PDF outline/bookmarks** (best if present)
2. **Table of Contents** detection (pages containing "Contents" / "Table of contents")
3. **Heading detection** from body text (numbered headings, title-like lines)

It outputs:

- `raw_text.txt` — all extracted text
- `sections.jsonl` — one JSON object per section `{id, title, level, start_page, end_page, text, path}`
- `tree.json` — hierarchical topic tree
- `tree.md` — human-readable outline

## Quick start (students)

### 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Put a PDF in `data/pdfs/`

Example:
```
data/pdfs/your_report.pdf
```

### 3) Parse it

```bash
python -m sustain_parser parse data/pdfs/your_report.pdf --out outputs/your_report
```

### 4) View the outline

Open:
- `outputs/your_report/tree.md`
- `outputs/your_report/sections.jsonl`

## Suggested student activities

Pick **one section node** and answer questions like:

- Where is **materiality** positioned (front/back)? Is it double materiality?
- How is **governance** described (board oversight, incentives, committees)?
- Are **metrics & targets** time-bound and baseline-disclosed?
- Evidence of external **assurance** (limited vs reasonable)?
- Which frameworks are referenced (GRI, SASB, ISSB/IFRS S1/S2, TCFD, ESRS)?
- “Greenwashing flags”: many claims but few quantified metrics; vague targets; missing Scope 3.

## Notes and limitations

- PDFs are messy. Different reports have different typography and numbering.
- This repo favors **transparent heuristics** over "magic".
- You can extend the heuristics for your chosen reports.

## License

MIT
