"""
backend/utils/claim_extractor.py
Extract structured claims from LLM generation output.
Uses safe_parse_json with multiple fallback strategies.
"""

from __future__ import annotations

import logging

from backend.models.claims import Claim, ClaimType
from backend.utils.json_parser import safe_parse_json, extract_json_array

logger = logging.getLogger(__name__)

VALID_CLAIM_TYPES = {"numeric", "temporal", "entity", "causal", "comparative", "general"}


def extract_claims_from_text(text: str, max_claims: int = 10) -> list[Claim]:
    """
    Parse claims from LLM output JSON.
    
    Expects a JSON array like:
    [{"claim_id": "C1", "claim_text": "...", "claim_type": "...", 
      "supporting_source_ids": [...], "confidence": 0.9}, ...]
    
    Returns empty list on failure — never raises.
    """
    if not text:
        return []

    raw = extract_json_array(text)
    if not raw:
        # Try as dict with "claims" key
        parsed = safe_parse_json(text)
        if isinstance(parsed, dict):
            raw = parsed.get("claims", [])

    if not raw or not isinstance(raw, list):
        logger.warning("claim_extractor: failed to parse claims from text")
        return []

    claims = []
    for i, item in enumerate(raw[:max_claims]):
        if not isinstance(item, dict):
            continue

        claim_type = item.get("claim_type", "general")
        if claim_type not in VALID_CLAIM_TYPES:
            claim_type = "general"

        try:
            claim = Claim(
                claim_id=item.get("claim_id", f"C{i + 1}"),
                claim_text=str(item.get("claim_text", "")).strip(),
                claim_type=claim_type,
                supporting_source_ids=item.get("supporting_source_ids", []),
                confidence=float(item.get("confidence", 0.8)),
            )
            if claim.claim_text:
                claims.append(claim)
        except Exception as e:
            logger.warning(f"claim_extractor: skipping malformed claim: {e}")
            continue

    return claims
