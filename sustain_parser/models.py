from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Section:
    """A parsed section of the report."""
    id: str
    title: str
    level: int
    start_page: int
    end_page: int
    text: str
    path: List[str] = field(default_factory=list)

    def to_record(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "path": self.path,
            "text": self.text,
        }


@dataclass
class Node:
    """Tree node for the outline."""
    title: str
    level: int
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    children: List["Node"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level,
            "start_page": self.start_page,
            "end_page": self.end_page,
            "children": [c.to_dict() for c in self.children],
        }
