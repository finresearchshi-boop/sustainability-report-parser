from __future__ import annotations

import re
from typing import Dict, List, Iterable, Optional, Tuple
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans


# -----------------------------
# 1) Framework mention scoring
# -----------------------------
FRAMEWORK_KEYWORDS: Dict[str, List[str]] = {
    "GRI": ["gri", "global reporting initiative"],
    "SASB": ["sasb"],
    "ISSB": ["issb", "ifrs s1", "ifrs s2", "ifrs sustainability", "international sustainability standards board"],
    "TCFD": ["tcfd", "task force on climate-related financial disclosures"],
    "ESRS": ["esrs", "csrd", "european sustainability reporting standards"],
}

def add_framework_counts(sections_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds columns: GRI, SASB, ISSB, TCFD, ESRS with counts per section.
    """
    df = sections_df.copy()
    low = df["text"].fillna("").str.lower()

    for name, phrases in FRAMEWORK_KEYWORDS.items():
        df[name] = 0
        for p in phrases:
            df[name] += low.str.count(re.escape(p))
    return df


# --------------------------------------------
# 2) Metric vs narrative proxies (greenwashing)
# --------------------------------------------
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
_PCT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_CCY_RE = re.compile(r"(?:£|\$|€)\s*\d+(?:,\d{3})*(?:\.\d+)?|\b(?:gbp|usd|eur)\s*\d+(?:,\d{3})*(?:\.\d+)?", re.IGNORECASE)

CLAIM_WORDS = [
    "commit", "committed", "aim", "aiming", "aspire", "aspiration", "strive", "plan", "plans",
    "target", "targets", "ambition", "promise", "pledge", "will", "intend", "intention",
    "seek", "seeking", "focus", "focused", "continue", "progress", "journey", "leading",
]

def metric_density(text: str) -> float:
    """
    Numbers per 1,000 characters (rough proxy for quantitative content).
    """
    nums = len(_NUM_RE.findall(text))
    return nums / max(1, len(text)) * 1000.0

def claim_density(text: str) -> float:
    """
    Claim/commitment words per 1,000 characters (rough proxy for narrative/PR tone).
    """
    low = text.lower()
    c = 0
    for w in CLAIM_WORDS:
        c += low.count(w)
    return c / max(1, len(text)) * 1000.0

def add_metric_narrative_proxies(sections_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - metric_density
      - claim_density
      - pct_count_per_1k
      - currency_count_per_1k
      - greenwash_score (claim_density - metric_density) [higher = more narrative relative to metrics]
    """
    df = sections_df.copy()
    texts = df["text"].fillna("")

    df["metric_density"] = texts.apply(metric_density)
    df["claim_density"] = texts.apply(claim_density)

    df["pct_count_per_1k"] = texts.apply(lambda t: len(_PCT_RE.findall(t)) / max(1, len(t)) * 1000.0)
    df["currency_count_per_1k"] = texts.apply(lambda t: len(_CCY_RE.findall(t)) / max(1, len(t)) * 1000.0)

    df["greenwash_score"] = df["claim_density"] - df["metric_density"]
    return df


# ----------------------------------------
# 3) Extract targets and timelines (regex)
# ----------------------------------------
TARGET_PATTERNS: List[Tuple[str, str]] = [
    (r"net\s*zero\s*by\s*(20\d{2})", "net_zero"),
    (r"carbon\s*neutral\s*by\s*(20\d{2})", "carbon_neutral"),
    (r"science[-\s]*based\s+target.*?(20\d{2})", "sbt_target"),
    (r"reduce(?:d)?\s+.*?\s+by\s+(20\d{2})", "reduce_by_year"),
    (r"target(?:s)?\s+.*?\s+(20\d{2})", "generic_target"),
    (r"baseline\s*(20\d{2})", "baseline_year"),
]

def extract_targets(sections_df: pd.DataFrame, window_before: int = 140, window_after: int = 220) -> pd.DataFrame:
    """
    Returns a table of target-like statements:
    section_id, title, page_range, year, metric_type, match, context, confidence
    """
    rows = []
    for _, r in sections_df.iterrows():
        text = (r.get("text") or "")
        low = text.lower()

        for pat, metric_type in TARGET_PATTERNS:
            for m in re.finditer(pat, low):
                year = m.group(1) if m.groups() else None
                start = max(0, m.start() - window_before)
                end = min(len(text), m.end() + window_after)
                ctx = text[start:end].replace("\n", " ")

                # simple confidence heuristic
                confidence = 0.6
                if metric_type in ("net_zero", "carbon_neutral", "sbt_target"):
                    confidence = 0.85
                if "scope" in ctx.lower() or "tco2" in ctx.lower() or "co2" in ctx.lower():
                    confidence = min(0.95, confidence + 0.05)

                rows.append({
                    "section_id": r["id"],
                    "title": r["title"],
                    "page_range": f'{r["start_page"]}-{r["end_page"]}',
                    "year": year,
                    "metric_type": metric_type,
                    "match": m.group(0),
                    "context": ctx,
                    "confidence": confidence,
                })
    return pd.DataFrame(rows)


# ---------------------------------------
# 4) Emissions extractor (Scope + units)
# ---------------------------------------
_SCOPE_RE = re.compile(r"\bscope\s*([123])\b", re.IGNORECASE)
_TCO2E_RE = re.compile(r"\b(\d+(?:,\d{3})*(?:\.\d+)?)\s*(tco2e|t\s*co2e|tonnes?\s*co2e|metric\s*tons?\s*co2e)\b", re.IGNORECASE)
_LOCATION_MARKET_RE = re.compile(r"\b(location[-\s]*based|market[-\s]*based)\b", re.IGNORECASE)

def extract_emissions_mentions(
    sections_df: pd.DataFrame,
    window_chars: int = 500
) -> pd.DataFrame:
    """
    Extracts snippets around Scope 1/2/3 mentions and tries to capture:
      - location-based vs market-based
      - tCO2e numbers/units (if present)
    Output columns:
      section_id, title, page_range, scope, snippet, basis, tco2e_values
    """
    rows = []
    for _, r in sections_df.iterrows():
        text = (r.get("text") or "")
        if not text:
            continue
        low = text.lower()

        for m in _SCOPE_RE.finditer(low):
            scope_num = m.group(1)
            start = max(0, m.start() - window_chars)
            end = min(len(text), m.end() + window_chars)
            snippet = text[start:end].replace("\n", " ")

            basis_match = _LOCATION_MARKET_RE.search(snippet)
            basis = basis_match.group(1).lower() if basis_match else None

            tco2e_vals = []
            for tm in _TCO2E_RE.finditer(snippet):
                tco2e_vals.append(f"{tm.group(1)} {tm.group(2)}")

            rows.append({
                "section_id": r["id"],
                "title": r["title"],
                "page_range": f'{r["start_page"]}-{r["end_page"]}',
                "scope": f"scope {scope_num}",
                "basis": basis,
                "tco2e_values": "; ".join(tco2e_vals) if tco2e_vals else None,
                "snippet": snippet,
            })

    return pd.DataFrame(rows)


# ---------------------------------------
# 5) Assurance and credibility flags
# ---------------------------------------
ASSURANCE_LEVEL_RE = re.compile(r"\b(limited assurance|reasonable assurance)\b", re.IGNORECASE)
ASSURANCE_PROVIDER_HINTS = [
    "deloitte", "pwc", "kpmg", "ernst & young", "ey", "bdo", "grant thornton",
    "dnv", "bureau veritas", "sgs", "lrqa", "tuv", "intertek",
]

def extract_assurance_flags(sections_df: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristic extractor returning:
      section_id, title, page_range,
      assurance_present, assurance_level, assurer, scope_keywords
    """
    rows = []
    for _, r in sections_df.iterrows():
        text = (r.get("text") or "")
        title = (r.get("title") or "")
        blob = f"{title}\n{text}".lower()

        present = ("assurance" in blob) or ("independent" in blob and "assurance" in blob)

        if not present:
            continue

        level_m = ASSURANCE_LEVEL_RE.search(blob)
        level = level_m.group(1).lower() if level_m else None

        assurer = None
        for a in ASSURANCE_PROVIDER_HINTS:
            if a in blob:
                assurer = a
                break

        # very simple scope keyword extraction
        scope_keywords = []
        for kw in ["ghg", "scope 1", "scope 2", "scope 3", "emissions", "safety", "injury", "water", "waste", "diversity", "pay gap"]:
            if kw in blob:
                scope_keywords.append(kw)

        rows.append({
            "section_id": r["id"],
            "title": r["title"],
            "page_range": f'{r["start_page"]}-{r["end_page"]}',
            "assurance_present": True,
            "assurance_level": level,
            "assurer": assurer,
            "scope_keywords": ", ".join(scope_keywords) if scope_keywords else None,
        })

    return pd.DataFrame(rows)


# ------------------------------------------------
# 6) Materiality finder + double materiality flag
# ------------------------------------------------
DOUBLE_MAT_HINTS = [
    "double materiality", "impact materiality", "financial materiality",
    "inside-out", "outside-in", "impacts, risks and opportunities", "iro",
]

def find_materiality_sections(sections_df: pd.DataFrame) -> pd.DataFrame:
    df = sections_df.copy()
    mask = df["title"].str.contains("material", case=False, na=False) | df["text"].str.contains(
        r"\bmateriality\b", case=False, na=False
    )
    return df[mask].sort_values(["start_page", "level"])

def add_double_materiality_flag(materiality_df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a boolean 'double_materiality' column using keyword heuristics.
    Input should usually be output of find_materiality_sections(df).
    """
    df = materiality_df.copy()
    blob = (df["title"].fillna("") + "\n" + df["text"].fillna("")).str.lower()
    df["double_materiality"] = False
    for h in DOUBLE_MAT_HINTS:
        df["double_materiality"] = df["double_materiality"] | blob.str.contains(re.escape(h))
    return df


# ------------------------------------------
# 7) Cross-references / index extraction
# ------------------------------------------
INDEX_TITLE_RE = re.compile(r"\b(index|content index|gri index|sasb index|tcfd index)\b", re.IGNORECASE)

def find_index_sections(sections_df: pd.DataFrame) -> pd.DataFrame:
    """
    Finds likely index sections such as "GRI Content Index" or "SASB Index".
    """
    df = sections_df.copy()
    mask = df["title"].str.contains(INDEX_TITLE_RE, na=False) | df["text"].str.contains(INDEX_TITLE_RE, na=False)
    return df[mask].sort_values(["start_page", "level"])

def extract_index_mentions(sections_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts lightweight evidence of index/cross-reference sections:
      section_id, title, page_range, index_type, snippet
    """
    rows = []
    idx_df = find_index_sections(sections_df)
    for _, r in idx_df.iterrows():
        text = (r.get("text") or "")
        low = (r.get("title") or "").lower() + "\n" + text.lower()

        index_type = None
        if "gri" in low:
            index_type = "GRI"
        elif "sasb" in low:
            index_type = "SASB"
        elif "tcfd" in low:
            index_type = "TCFD"
        elif "issb" in low or "ifrs s" in low:
            index_type = "ISSB"
        else:
            index_type = "Index"

        snippet = text[:1200].replace("\n", " ")
        rows.append({
            "section_id": r["id"],
            "title": r["title"],
            "page_range": f'{r["start_page"]}-{r["end_page"]}',
            "index_type": index_type,
            "snippet": snippet,
        })

    return pd.DataFrame(rows)


# -----------------------------
# 8) Topic clustering (optional)
# -----------------------------
def cluster_sections(
    sections_df: pd.DataFrame,
    k: int = 6,
    max_features: int = 4000,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Topic clustering using TF-IDF + KMeans (teachable; no LLM).
    Adds 'cluster' column.
    """
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
