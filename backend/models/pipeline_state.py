"""
backend/models/pipeline_state.py
The central data contract passed through all 9 pipeline stages.
Every stage reads from PipelineState and writes its results back to it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from backend.models.claims import Claim, VerificationResult
from backend.models.documents import Document
from backend.models.provenance import ProvenanceRecord


StageStatus = Literal["pending", "running", "complete", "failed", "skipped"]


@dataclass
class IntentResult:
    intent_type: Literal["factual", "analytical", "creative", "conversational", "code"]
    needs_web_search: bool
    is_high_stakes: bool
    claim_types: list[str]
    domain: str
    confidence: float


@dataclass
class StageLog:
    stage_number: int
    stage_name: str
    status: StageStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: str = ""
    detail: dict = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class PipelineState:
    # ── Core identifiers ──────────────────────────────────────────────────────
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str = ""
    user_id: str = ""
    original_query: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)

    # ── Stage outputs (populated as pipeline progresses) ──────────────────────
    intent: Optional[IntentResult] = None
    search_queries: list[str] = field(default_factory=list)
    reprompt_template: Optional[str] = None
    raw_documents: list[Document] = field(default_factory=list)
    reranked_documents: list[Document] = field(default_factory=list)
    context_block: Optional[str] = None
    raw_generation: Optional[str] = None
    reasoning_trace: Optional[str] = None   # DeepSeek-R1 <think> block
    claims: list[Claim] = field(default_factory=list)
    verification_results: list[VerificationResult] = field(default_factory=list)
    provenance: Optional[ProvenanceRecord] = None
    final_answer: Optional[str] = None

    # ── Intelligence Engine logs — one per stage ──────────────────────────────
    stage_logs: list[StageLog] = field(default_factory=list)

    # ── Runtime tracking ──────────────────────────────────────────────────────
    pipeline_run_id: Optional[str] = None   # Supabase pipeline_runs row ID
    total_start_ms: Optional[float] = None
