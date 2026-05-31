"""
backend/models/documents.py
Document and SearchResult dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Document:
    doc_id: str
    source: Literal["web", "vector_db"]
    url: str
    title: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    relevance_score: float = 0.0
    embedding: Optional[list[float]] = None
    authority_tag: str = "standard"   # "high" | "standard"


@dataclass
class SearchResult:
    url: str
    title: str
    snippet: str
    domain: str
    published_date: Optional[str] = None
    position: int = 0
