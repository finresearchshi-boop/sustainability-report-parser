# Sustainability Report Parser

A Python package for teaching and research: parse a sustainability
report PDF into a **hierarchical topic tree** (sections/sub-sections),
extract **section-level text**, and export **figures** and **tables**.
Results are ready for analysis in **pandas**.

## What you get

Given a PDF, the parser attempts (in order):

1.  **PDF outline/bookmarks** (best case)
2.  **Table of Contents** detection (common in reports)
3.  **Heading detection** from body text (fallback)

Outputs and objects include:

-   `tree_md` (pretty outline)
-   `sections` (each section with title/level/page range/text/path)
-   `sections_df()` → pandas DataFrame
-   optional exports:
    -   `figures/` (extracted embedded images)
    -   `tables/` (extracted tables as CSVs when possible)

> Note: PDFs vary a lot. Scanned PDFs (image-only) are harder without
> OCR.

------------------------------------------------------------------------

# Installation (recommended: Anaconda / Conda)

This repo includes an `environment.yml` that aims for **click-and-run**.

## Windows (Anaconda Prompt)

1.  Install Anaconda or Miniconda.
2.  Download this repo (GitHub → Code → Download ZIP) and unzip.
3.  Open **Anaconda Prompt** and `cd` into the repo folder, then:

``` bash
conda env create -f environment.yml
conda activate sustainpdf
jupyter lab
```

## macOS / Ubuntu (Terminal)

``` bash
conda env create -f environment.yml
conda activate sustainpdf
jupyter lab
```

### VS Code (optional)

-   Install the Python extension
-   Select interpreter: `sustainpdf`
-   Open and run: `notebooks/00_quickstart.ipynb`

### Spyder (optional)

-   Launch Spyder from the `sustainpdf` environment (Anaconda
    Navigator), or configure Spyder to use the `sustainpdf` interpreter.

------------------------------------------------------------------------

# Quickstart (Python)

``` python
import sustain_parser as sp

pdf_path = "data/pdfs/your_report.pdf"
res = sp.parse_pdf(pdf_path)

print("Strategy:", res.strategy_used, "| pages:", res.page_count)
print("\n".join(res.tree_md.splitlines()[:80]))
```

## Convert to pandas

``` python
df = res.sections_df()
df[["level", "title", "start_page", "end_page", "n_words"]].head(20)
```

## Find and extract a section

``` python
mask = df["title"].str.contains("material", case=False, na=False)
section_id = df.loc[mask, "id"].iloc[0]
text = df.loc[df["id"] == section_id, "text"].iloc[0]
print(text[:1200])
```

## Export outputs

``` python
res.export("outputs/my_report")
res.export_assets("outputs/my_report", export_figures=True, export_tables=True)
```

------------------------------------------------------------------------

# Troubleshooting

### 1) `ModuleNotFoundError: No module named 'fitz'`

PyMuPDF did not install correctly.

Fix:

``` bash
conda activate sustainpdf
pip install pymupdf
```

### 2) Jupyter cannot find `sustainpdf` kernel

Run:

``` bash
conda activate sustainpdf
python -m ipykernel install --user --name sustainpdf --display-name "Python (sustainpdf)"
```

Restart JupyterLab and choose the kernel.

### 3) `conda env create` fails

Try updating conda:

``` bash
conda update -n base -c defaults conda
```

Then recreate the environment.

### 4) Windows path errors

Avoid spaces in file paths. Example:

GOOD:

    C:\reports\unilever.pdf

BAD:

    C:\Users\My Documents\Sustainability Reports\file.pdf

### 5) Empty or nonsense text extracted

Your PDF is likely **scanned (image-only)**.\
You can test by trying to select text in the PDF viewer. If you cannot
select text, the parser cannot read it without OCR.

### 6) Tables not extracted

This is normal. Many sustainability reports embed tables as images. The
parser only extracts real text tables.

### 7) Very slow execution

Some reports exceed 200 pages. For class use, limit table extraction:

``` python
res.export_assets("outputs", table_max_pages=30)
```

### 8) Mac M‑series (Apple Silicon) issues

Always activate the environment before running Python:

``` bash
conda activate sustainpdf
```

------------------------------------------------------------------------

# License

MIT
