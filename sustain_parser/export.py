from __future__ import annotations

from typing import List
import os
import json

from .models import Node, Section


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_raw_text(out_dir: str, pages_text: List[str]) -> str:
    ensure_dir(out_dir)
    p = os.path.join(out_dir, "raw_text.txt")
    with open(p, "w", encoding="utf-8") as f:
        for i, t in enumerate(pages_text, start=1):
            f.write(f"\n\n===== PAGE {i} =====\n\n")
            f.write(t.rstrip() + "\n")
    return p


def write_tree_json(out_dir: str, root: Node) -> str:
    ensure_dir(out_dir)
    p = os.path.join(out_dir, "tree.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(root.to_dict(), f, ensure_ascii=False, indent=2)
    return p


def write_tree_md(out_dir: str, tree_md: str) -> str:
    ensure_dir(out_dir)
    p = os.path.join(out_dir, "tree.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(tree_md)
    return p


def write_sections_jsonl(out_dir: str, sections: List[Section]) -> str:
    ensure_dir(out_dir)
    p = os.path.join(out_dir, "sections.jsonl")
    with open(p, "w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(s.to_record(), ensure_ascii=False) + "\n")
    return p
