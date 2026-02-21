from __future__ import annotations

from typing import List, Tuple, Optional, Dict
import re
import hashlib

from .models import Node, Section


def build_tree_from_entries(entries: List[Tuple[int, str, int]]) -> Node:
    """
    Build a hierarchical tree from (level, title, page_1_indexed) entries.
    """
    root = Node(title="ROOT", level=0, start_page=None, end_page=None)
    stack: List[Node] = [root]

    for level, title, page in entries:
        node = Node(title=title.strip(), level=level, start_page=page, end_page=None)

        # Pop until parent level < current level
        while stack and stack[-1].level >= level:
            stack.pop()
        parent = stack[-1] if stack else root
        parent.children.append(node)
        stack.append(node)

    return root


def _assign_end_pages(node: Node, doc_page_count: int) -> None:
    """
    Assign end_page for each node based on next sibling's start_page - 1.
    Depth-first.
    """
    children = node.children
    for idx, child in enumerate(children):
        if idx + 1 < len(children):
            child.end_page = max(child.start_page or 1, (children[idx + 1].start_page or child.start_page or 1) - 1)
        else:
            # last child ends at parent's end, or doc end
            child.end_page = node.end_page if node.end_page is not None else doc_page_count
        _assign_end_pages(child, doc_page_count)


def finalize_tree(root: Node, doc_page_count: int) -> Node:
    # Root spans whole doc
    root.start_page = 1
    root.end_page = doc_page_count
    _assign_end_pages(root, doc_page_count)
    return root


def flatten_sections(root: Node, pages_text: List[str]) -> List[Section]:
    """
    Produce a list of Section objects from the finalized tree.
    Uses page ranges to slice text.
    """
    sections: List[Section] = []

    def walk(node: Node, path: List[str]):
        for child in node.children:
            child_path = path + [child.title]
            sp = max(1, child.start_page or 1)
            ep = max(sp, child.end_page or sp)
            # slice pages_text (0-index)
            text = "\n".join(pages_text[sp - 1: ep]).strip()
            sid = hashlib.sha1((" > ".join(child_path) + f"|{sp}|{ep}").encode("utf-8")).hexdigest()[:12]
            sections.append(
                Section(
                    id=sid,
                    title=child.title,
                    level=child.level,
                    start_page=sp,
                    end_page=ep,
                    text=text,
                    path=child_path,
                )
            )
            walk(child, child_path)

    walk(root, [])
    return sections


def tree_to_markdown(root: Node) -> str:
    """
    Pretty markdown outline.
    """
    lines: List[str] = []
    def rec(node: Node, indent: int = 0):
        for ch in node.children:
            sp = ch.start_page if ch.start_page is not None else "?"
            ep = ch.end_page if ch.end_page is not None else "?"
            lines.append(f'{"  " * indent}- {ch.title}  *(pp. {sp}–{ep})*')
            rec(ch, indent + 1)
    rec(root, 0)
    return "\n".join(lines).strip() + "\n"
