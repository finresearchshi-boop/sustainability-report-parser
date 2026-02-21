from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any

import pandas as pd
import fitz  # PyMuPDF
import pdfplumber


def extract_figures(pdf_path: str, out_dir: str) -> pd.DataFrame:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    rows: List[Dict[str, Any]] = []

    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        images = page.get_images(full=True)
        for img_i, img in enumerate(images):
            xref = img[0]
            base = doc.extract_image(xref)
            ext = base.get("ext", "png")
            img_bytes = base["image"]

            file_path = out / f"page_{page_index+1:03d}_img_{img_i:02d}.{ext}"
            file_path.write_bytes(img_bytes)

            rows.append(
                {
                    "page": page_index + 1,
                    "image_index": img_i,
                    "xref": xref,
                    "file_path": str(file_path),
                    "ext": ext,
                    "width": base.get("width"),
                    "height": base.get("height"),
                }
            )

    return pd.DataFrame(rows)


def extract_tables(
    pdf_path: str,
    out_dir: str,
    max_pages: Optional[int] = None,
) -> pd.DataFrame:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        n_pages = len(pdf.pages)
        if max_pages is not None:
            n_pages = min(n_pages, max_pages)

        for page_i in range(n_pages):
            page = pdf.pages[page_i]
            tables = page.extract_tables() or []
            for t_i, table in enumerate(tables):
                df = pd.DataFrame(table)
                csv_path = out / f"page_{page_i+1:03d}_table_{t_i:02d}.csv"
                df.to_csv(csv_path, index=False)

                rows.append(
                    {
                        "page": page_i + 1,
                        "table_index": t_i,
                        "csv_path": str(csv_path),
                        "n_rows": int(df.shape[0]),
                        "n_cols": int(df.shape[1]),
                    }
                )

    return pd.DataFrame(rows)
