"""
backend/models/claims.py
Claim and VerificationResult dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


ClaimType = Literal["numeric", "temporal", "entity", "causal", "comparative", "general"]
Verdict = Literal["VERIFIED", "UNCERTAIN", "CONTRADICTED"]


@dataclass
class Claim:
    claim_id: str                              # "C1", "C2", etc.
    claim_text: str
    claim_type: ClaimType
    supporting_source_ids: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class VerificationResult:
    claim_id: str
    claim_text: str
    verdict: Verdict
    confidence: float
    reasoning: str = ""
    supporting_text: Optional[str] = None
    contradicting_text: Optional[str] = None
    supporting_source_ids: list[str] = field(default_factory=list)
    verifier_model: str = ""
    # Numeric-specific fields (from arithmetic checker)
    claim_value: Optional[str] = None
    source_value: Optional[str] = None
    unit_match: Optional[bool] = None
    # Temporal-specific fields
    claim_date: Optional[str] = None
    source_date: Optional[str] = None
    is_consistent: Optional[bool] = None
