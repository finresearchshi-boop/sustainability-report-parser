# Sustainability Report Parser (`sustain-parser`)

A teaching-friendly Python package for sustainability accounting / ESG disclosure analysis. It parses a sustainability report PDF into:

- a **hierarchical section tree** (topics → sub-topics)
- **section-level text** (ready for textual analysis)
- optional export of **figures** and **tables** (when detectable)
- **pandas DataFrames** for quick exploration in Jupyter / Spyder / VS Code

This package is designed to be transparent (heuristics + regex + TF‑IDF clustering), so students can understand *how* the extraction works.

---

## Install

### Option A (recommended for students): one command

```bash
pip install sustain-parser
```

Verify:

```bash
python -c "import sustain_parser as sp; print(sp.__version__)"
```

> `pip install sustain-parser` installs required dependencies automatically (including `pymupdf` and `pdfplumber`).

### Option B (recommended for class labs): conda environment + JupyterLab

```bash
conda create -n sustainpdf python=3.11 -y
conda activate sustainpdf
pip install sustain-parser jupyterlab
jupyter lab
```

### VS Code / Spyder / Jupyter kernel notes

**VS Code**
- Command Palette → **Python: Select Interpreter**
- choose the interpreter under `.../envs/sustainpdf/...` (if you use the conda option)

**Spyder**
- launch from the same environment:
  ```bash
  conda activate sustainpdf
  spyder
  ```
  (or configure Spyder’s interpreter to the `sustainpdf` environment)

**Jupyter kernel (if imports fail)**
```bash
conda activate sustainpdf
python -m pip install -U ipykernel
python -m ipykernel install --user --name sustainpdf --display-name "Python (sustainpdf)"
```
Then in Jupyter: **Kernel → Change Kernel → Python (sustainpdf)**

---

## Quickstart: parse a report PDF into a tree + DataFrame

### 1) Parse a PDF

```python
import sustain_parser as sp

pdf_path = "data/pdfs/your_report.pdf"
res = sp.parse_pdf(pdf_path)

print("Strategy used:", res.strategy_used)
print("Pages:", res.page_count)
print("\n".join(res.tree_md.splitlines()[:80]))  # preview the tree
```

### 2) Get the section DataFrame

```python
df = res.sections_df()
df[["id", "level", "title", "start_page", "end_page", "n_words", "path"]].head(20)
```

**Typical columns**
- `id`: stable section id
- `level`: heading depth (1=top level)
- `title`: section heading/title
- `path`: full hierarchical path like `"Report > Climate > Targets"`
- `start_page`, `end_page`: approximate page range
- `text`: extracted section text
- `n_words`: word count of `text`

---

## Build/inspect the tree

The parse result already includes a markdown tree (`res.tree_md`) and structured data (`res.tree_json`).

```python
print(res.tree_md)        # pretty tree (markdown)
tree = res.tree_json      # dict-like structure (json-serializable)
```

Export tree files:

```python
res.export("outputs/my_report")
# outputs/my_report/tree.md
# outputs/my_report/tree.json
# outputs/my_report/sections.jsonl
# outputs/my_report/raw_text.txt
```

---

## Extract text under a particular element of the tree

### A) Find a section by title keyword, then read its text

```python
mask = df["title"].str.contains("material", case=False, na=False)
df[mask][["id", "title", "start_page", "end_page"]].head(10)
```

Pick one section:

```python
section_id = df.loc[mask, "id"].iloc[0]
section_text = df.loc[df["id"] == section_id, "text"].iloc[0]
print(section_text[:1500])
```

### B) Extract *all text* under a subtree using the `path` column

Example: everything under “climate” (works even if the tree differs across firms):

```python
climate_df = df[df["path"].str.contains("climate", case=False, na=False)]
all_climate_text = "\n\n".join(climate_df["text"].tolist())
len(all_climate_text)
```

### C) Save a subtree to a DataFrame for later NLP

```python
sub_df = df[df["path"].str.contains("governance", case=False, na=False)].copy()
sub_df.to_csv("outputs/governance_sections.csv", index=False)
```

---

## Export figures and tables (optional)

Many sustainability reports embed charts/tables as images. Extraction depends on PDF structure.

```python
res.export_assets(
    out_dir="outputs/my_report",
    export_figures=True,
    export_tables=True,
    table_max_pages=30,  # keep small for classroom runs
)

res.figures_df.head()  # metadata about extracted figures
res.tables_df.head()   # metadata about extracted tables
```

---

# Analysis helpers (`sustain_parser.analysis`)

Import once:

```python
from sustain_parser import analysis as ana
```

Below are examples for **each** analysis function.

---

## 1) Framework mention scoring (GRI / SASB / ISSB / TCFD / ESRS)

Counts mentions per section.

```python
df_fw = ana.add_framework_counts(df)
df_fw[["title","GRI","SASB","ISSB","TCFD","ESRS"]].sort_values("GRI", ascending=False).head(10)
```

---

## 2) Metric vs narrative proxies (“greenwashing” lens)

Adds:
- `metric_density` (numbers per 1,000 chars)
- `claim_density` (commit/aim/strive words per 1,000 chars)
- `%` density, currency density
- `greenwash_score = claim_density - metric_density`

```python
df_gw = ana.add_metric_narrative_proxies(df)
df_gw[["title","metric_density","claim_density","greenwash_score"]].sort_values("greenwash_score", ascending=False).head(15)
```

Interpretation (teachable): high `greenwash_score` suggests more **narrative/claims** relative to **numbers**, but it is only a heuristic.

---

## 3) Extract targets and timelines

Returns a table: `section_id, year, metric_type, confidence, context`.

```python
targets = ana.extract_targets(df)
targets.head(20)
```

Common classroom tasks:
- compare targets across firms
- map targets to which section they appear in
- discuss whether targets are measurable, time-bound, baseline-defined

---

## 4) Emissions-specific extractor (Scope 1/2/3 + basis + tCO2e)

Extracts snippets around scope mentions and tries to capture:
- scope (1/2/3)
- `location-based` / `market-based` (if mentioned)
- tCO2e unit patterns (if present)

```python
em = ana.extract_emissions_mentions(df)
em.head(20)
```

---

## 5) Assurance and credibility flags

Finds assurance sections and extracts simple structured signals:
- assurance level (limited / reasonable, if mentioned)
- provider name (heuristic list)
- scope keywords (e.g., ghg, water, safety)

```python
assurance = ana.extract_assurance_flags(df)
assurance.head(20)
```

---

## 6) Materiality finder + double materiality flag

```python
mat = ana.find_materiality_sections(df)
mat2 = ana.add_double_materiality_flag(mat)
mat2[["title","start_page","end_page","double_materiality"]].head(20)
```

---

## 7) Cross-references / index extraction (GRI index / SASB index)

Find likely index sections:

```python
idx_sections = ana.find_index_sections(df)
idx_sections[["title","start_page","end_page"]].head(10)
```

Extract a lightweight index mention table:

```python
idx_mentions = ana.extract_index_mentions(df)
idx_mentions.head(20)
```

---

## 8) Simple topic clustering (TF‑IDF + KMeans)

A transparent, non‑LLM method to group sections into themes.

```python
clustered = ana.cluster_sections(df, k=6)
clustered[["cluster","title","start_page","end_page"]].sort_values(["cluster","start_page"]).head(30)
```

---

## Troubleshooting

### 1) `ModuleNotFoundError` (e.g. `pdfplumber`)
Install/repair in the same environment that runs your notebook/script:

```bash
pip install -U sustain-parser
```

Then restart the kernel / restart Spyder / restart VS Code Python session.

### 2) Jupyter uses the wrong Python
In a notebook cell:

```python
import sys
print(sys.executable)
```

If it shows `/opt/anaconda3/bin/python` (base), switch kernel to your environment or launch Jupyter from the environment:

```bash
conda activate sustainpdf
jupyter lab
```

### 3) Empty or nonsense extracted text
Your PDF is likely **scanned (image-only)**. This package does not run OCR by default.

Quick test: can you select/copy text in the PDF viewer?
- **Yes** → should work
- **No** → OCR is required (future extension)

### 4) Tables/figures not exported
Many “tables” are images. Extraction depends on PDF structure.

### 5) Slow runs in class
Use smaller PDFs (≤150 pages) and limit table parsing:

```python
res.export_assets("outputs/my_report", export_tables=True, table_max_pages=30)
```

---

## License
MIT
