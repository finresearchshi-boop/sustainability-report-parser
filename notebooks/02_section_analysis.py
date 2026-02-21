# Demo: simple section analysis (no NLP libraries required)
# Run after parsing:
#   python notebooks/02_section_analysis.py outputs/your_report/sections.jsonl

import sys, json, re
from collections import Counter

KEYWORDS = {
    "GRI": ["gri"],
    "SASB": ["sasb"],
    "ISSB": ["issb", "ifrs s1", "ifrs s2"],
    "TCFD": ["tcfd"],
    "ESRS": ["esrs", "csrd"],
    "SCOPE": ["scope 1", "scope 2", "scope 3"],
    "MATERIALITY": ["materiality", "double materiality"],
    "ASSURANCE": ["assurance", "limited assurance", "reasonable assurance"],
}

def count_hits(text: str, phrases):
    t = text.lower()
    return sum(t.count(p) for p in phrases)

def metric_density(text: str) -> float:
    # very rough proxy: numbers per 1,000 chars
    nums = len(re.findall(r"\b\d+(?:\.\d+)?%?\b", text))
    return nums / max(1, len(text)) * 1000

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python notebooks/02_section_analysis.py outputs/.../sections.jsonl")
        raise SystemExit(1)

    path = sys.argv[1]
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            text = r.get("text","")
            row = {
                "id": r["id"],
                "title": r["title"],
                "level": r["level"],
                "pages": f'{r["start_page"]}-{r["end_page"]}',
                "chars": len(text),
                "metric_density": round(metric_density(text), 3),
            }
            for k, phrases in KEYWORDS.items():
                row[k] = count_hits(text, phrases)
            rows.append(row)

    # Print top sections by metric density
    rows_sorted = sorted(rows, key=lambda x: x["metric_density"], reverse=True)
    print("\nTop sections by metric density (numbers per 1,000 chars):")
    for r in rows_sorted[:10]:
        print(f'  {r["metric_density"]:>6}  | {r["title"]}  (pp. {r["pages"]})')

    # Print sections mentioning Scope 3
    scope3 = [r for r in rows if r["SCOPE"] > 0]
    print(f"\nSections mentioning Scope terms: {len(scope3)}")
    for r in scope3[:10]:
        print(f'  ScopeHits={r["SCOPE"]:<3} | {r["title"]} (pp. {r["pages"]})')
