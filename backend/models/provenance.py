"""
backend/models/provenance.py
ProvenanceRecord and SourceRef dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class SourceRef:
    source_id: str           # e.g. "SOURCE_1"
    url: str
    title: str
    domain: str
    snippet: str
    retrieved_at: datetime
    content_hash: str        # SHA-256 of the snippet text at retrieval time
    claim_ids: list[str] = field(default_factory=list)
    published_date: Optional[str] = None
    authority_tag: str = "standard"


@dataclass
class ProvenanceRecord:
    run_id: str
    conversation_id: str
    query_hash: str              # SHA-256 of original_query
    sources: list[SourceRef] = field(default_factory=list)
    verification_summary: dict = field(default_factory=dict)  # {"VERIFIED": N, ...}
    models_used: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    pipeline_version: str = "v1.0.0"
