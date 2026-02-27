from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Paper:
    source: str
    title: str
    url: str
    published: datetime
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    identifier: str = ""
    doi: str = ""
    query: str = ""
    relevance: float = 0.0

    @property
    def normalized_title(self) -> str:
        return " ".join(self.title.lower().strip().split())

