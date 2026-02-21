from __future__ import annotations

import re
from typing import Dict, List
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


FRAMEWORK_KEYWORDS: Dict[str, List[str]] = {
    "GRI": ["gri", "global reporting initiative"],
    "SASB": ["sasb"],
    "ISSB": ["issb", "ifrs s1", "ifrs s2"],
    "TCFD": ["tcfd", "task force on climate-related financial disclosures"],
    "ESRS": ["esrs", "csrd"],
}


def metric_density(text: str) -> float:
    nums = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
    return nums / max(1, len(text)) * 1000.0


def add_framework_counts(sections_df: pd.DataFrame) -> pd.DataFrame:
    df = sections_df.copy()
    low = df["text"].fillna("").str.lower()

    for name, phrases in FRAMEWORK_KEYWORDS.items():
        df[name] = 0
        for p in phrases:
            df[name] += low.str.count(re.escape(p))

    return df


def add_metric_density(sections_df: pd.DataFrame) -> pd.DataFrame:
    df = sections_df.copy()
    df["metric_density"] = df["text"].fillna("").apply(metric_density)
    return df


def find_materiality_sections(sections_df: pd.DataFrame) -> pd.DataFrame:
    df = sections_df.copy()
    mask = df["title"].str.contains("material", case=False, na=False) | df["text"].str.contains(
        r"\bmateriality\b", case=False, na=False
    )
    return df[mask].sort_values(["start_page", "level"])


def find_assurance_sections(sections_df: pd.DataFrame) -> pd.DataFrame:
    df = sections_df.copy()
    mask = df["title"].str.contains("assurance", case=False, na=False) | df["text"].str.contains(
        r"\bassurance\b", case=False, na=False
    )
    return df[mask].sort_values(["start_page", "level"])


def scope_snippets(sections_df: pd.DataFrame, window_chars: int = 450) -> pd.DataFrame:
    rows = []
    for _, r in sections_df.iterrows():
        text = (r.get("text") or "")
        low = text.lower()
        for m in re.finditer(r"(scope\s*[123])", low):
            start = max(0, m.start() - window_chars)
            end = min(len(text), m.end() + window_chars)
            rows.append(
                {
                    "section_id": r["id"],
                    "title": r["title"],
                    "page_range": f'{r["start_page"]}-{r["end_page"]}',
                    "scope": low[m.start():m.end()],
                    "snippet": text[start:end].replace("\n", " "),
                }
            )
    return pd.DataFrame(rows)


TARGET_PATTERNS = [
    r"net\s*zero\s*by\s*(20\d{2})",
    r"carbon\s*neutral\s*by\s*(20\d{2})",
    r"reduce(?:d)?\s+.*?\s+by\s+(20\d{2})",
    r"target(?:s)?\s+.*?\s+(20\d{2})",
]


def extract_targets(sections_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in sections_df.iterrows():
        text = (r.get("text") or "")
        for pat in TARGET_PATTERNS:
            for m in re.finditer(pat, text.lower()):
                yr = m.group(1) if m.groups() else None
                start = max(0, m.start() - 120)
                end = min(len(text), m.end() + 180)
                rows.append(
                    {
                        "section_id": r["id"],
                        "title": r["title"],
                        "page_range": f'{r["start_page"]}-{r["end_page"]}',
                        "year": yr,
                        "match": m.group(0),
                        "context": text[start:end].replace("\n", " "),
                    }
                )
    return pd.DataFrame(rows)


def cluster_sections(
    sections_df: pd.DataFrame,
    k: int = 6,
    max_features: int = 4000,
    random_state: int = 42,
) -> pd.DataFrame:
    df = sections_df.copy()
    texts = df["text"].fillna("").tolist()

    vec = TfidfVectorizer(
        max_features=max_features,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
    )
    X = vec.fit_transform(texts)

    km = KMeans(n_clusters=k, n_init="auto", random_state=random_state)
    labels = km.fit_predict(X)

    df["cluster"] = labels
    return df
