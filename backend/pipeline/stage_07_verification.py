"""
backend/pipeline/stage_07_verification.py
Stage 7: Verification — LLM as Judge
Independently verifies each factual claim against retrieved evidence.
Uses Gemma-3-12B (different model family = different blind spots).
Ensemble mode for high-stakes queries.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from backend.config import settings
from backend.models.claims import Claim, VerificationResult
from backend.models.documents import Document
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import openrouter_client
from backend.utils.json_parser import safe_parse_json

logger = logging.getLogger(__name__)

RATE_LIMIT_SLEEP = 1.5  # seconds between calls to respect free tier rate limit


def _build_sources_context(docs: list[Document], source_ids: list[str]) -> list[dict]:
    """Build relevant source context for a claim."""
    # Find docs matching the claim's source IDs
    relevant = []
    for i, doc in enumerate(docs):
        source_id = f"SOURCE_{i + 1}"
        if source_id in source_ids or not source_ids:
            relevant.append({
                "source_id": source_id,
                "title": doc.title,
                "domain": doc.domain,
                "date": doc.published_date or "unknown",
                "snippet": doc.snippet[:500],
            })

    # Always include top 3 reranked docs as context
    for i, doc in enumerate(docs[:3]):
        source_id = f"SOURCE_{i + 1}"
        if not any(s["source_id"] == source_id for s in relevant):
            relevant.append({
                "source_id": source_id,
                "title": doc.title,
                "domain": doc.domain,
                "date": doc.published_date or "unknown",
                "snippet": doc.snippet[:500],
            })

    return relevant[:5]  # Max 5 sources per claim verification


def _format_sources_for_prompt(sources: list[dict]) -> str:
    lines = []
    for s in sources:
        lines.append(f"[{s['source_id']}] {s['title']} ({s['domain']}, {s['date']})")
        lines.append(f'"{s["snippet"]}"')
        lines.append("")
    return "\n".join(lines)


def _parse_verdict(parsed: dict, claim: Claim, model: str) -> VerificationResult:
    """Parse an LLM verification response into a VerificationResult."""
    verdict = parsed.get("verdict", "UNCERTAIN")
    if verdict not in ("VERIFIED", "UNCERTAIN", "CONTRADICTED"):
        verdict = "UNCERTAIN"

    return VerificationResult(
        claim_id=claim.claim_id,
        claim_text=claim.claim_text,
        verdict=verdict,
        confidence=float(parsed.get("confidence", 0.5)),
        reasoning=parsed.get("reasoning", ""),
        supporting_text=parsed.get("supporting_text"),
        contradicting_text=parsed.get("contradicting_text"),
        supporting_source_ids=parsed.get("supporting_source_ids", []),
        verifier_model=model,
        claim_value=parsed.get("claim_value"),
        source_value=parsed.get("source_value"),
        unit_match=parsed.get("unit_match"),
        claim_date=parsed.get("claim_date"),
        source_date=parsed.get("source_date"),
        is_consistent=parsed.get("is_consistent"),
    )


async def _verify_single_claim(
    claim: Claim,
    docs: list[Document],
    prompt_template: str,
    model: str,
    system_prompt: str,
) -> VerificationResult:
    """Verify one claim. Returns UNCERTAIN on any error."""
    try:
        sources = _build_sources_context(docs, claim.supporting_source_ids)
        sources_text = _format_sources_for_prompt(sources)

        prompt = (
            prompt_template
            .replace("{{ claim_text }}", claim.claim_text)
            .replace("{{ claim_type }}", claim.claim_type)
            .replace("{% for source in relevant_sources %}\n[{{ source.source_id }}] {{ source.title }} ({{ source.domain }}, {{ source.date }})\n\"{{ source.snippet }}\"\n\n{% endfor %}", sources_text)
        )

        response = await openrouter_client.chat_completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt,
            temperature=0.0,
            max_tokens=512,
        )

        parsed = safe_parse_json(response)
        if not parsed or not isinstance(parsed, dict):
            raise ValueError(f"Could not parse verifier response: {response[:200]}")

        return _parse_verdict(parsed, claim, model)

    except Exception as e:
        logger.warning(f"Verification failed for claim {claim.claim_id}: {e}")
        return VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            verdict="UNCERTAIN",
            confidence=0.0,
            reasoning=f"Verification error: {e}",
            verifier_model=model,
        )


class Stage07Verification(BaseStage):
    stage_number = 7
    stage_name = "Verification"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            claims = state.claims
            docs = state.reranked_documents
            intent = state.intent

            # Skip verification for code and conversational intents
            if intent and intent.intent_type in ("conversational", "code"):
                state.verification_results = []
                self.log(
                    state,
                    status="skipped",
                    summary=f"Skipped — {intent.intent_type} queries don't need fact verification.",
                    started_at=started_at,
                )
                return state

            if not claims:
                state.verification_results = []
                self.log(
                    state,
                    status="complete",
                    summary="No claims to verify.",
                    started_at=started_at,
                )
                return state

            # Load prompts
            main_verifier_prompt = self.load_prompt("prompts/verification/v1_claim_verifier.md")
            arithmetic_prompt = self.load_prompt("prompts/verification/v1_arithmetic_checker.md")
            temporal_prompt = self.load_prompt("prompts/verification/v1_temporal_checker.md")
            system_prompt = self.load_prompt("prompts/system/verifier_base.md")

            is_high_stakes = intent.is_high_stakes if intent else False
            results: list[VerificationResult] = []

            for i, claim in enumerate(claims[: settings.pipeline_max_claims]):
                # Rate limit between calls
                if i > 0:
                    await asyncio.sleep(RATE_LIMIT_SLEEP)

                # Choose prompt based on claim type
                if claim.claim_type == "numeric":
                    prompt = arithmetic_prompt
                elif claim.claim_type == "temporal":
                    prompt = temporal_prompt
                else:
                    prompt = main_verifier_prompt

                # Primary verification
                result = await _verify_single_claim(
                    claim, docs, prompt, settings.model_verification, system_prompt
                )

                 # Ensemble mode for high-stakes queries (production only to protect dev rate limits)
                if is_high_stakes and settings.app_env == "production" and result.verdict != "UNCERTAIN":
                    await asyncio.sleep(RATE_LIMIT_SLEEP)
                    result2 = await _verify_single_claim(
                        claim, docs, prompt, settings.model_intent, system_prompt
                    )
                    # If verdicts disagree → UNCERTAIN
                    if result2.verdict != result.verdict:
                        result.verdict = "UNCERTAIN"
                        result.reasoning = (
                            f"Ensemble disagreement: {settings.model_verification}→{result.verdict}, "
                            f"{settings.model_intent}→{result2.verdict}"
                        )

                results.append(result)

            state.verification_results = results

            verified = sum(1 for r in results if r.verdict == "VERIFIED")
            uncertain = sum(1 for r in results if r.verdict == "UNCERTAIN")
            contradicted = sum(1 for r in results if r.verdict == "CONTRADICTED")

            self.log(
                state,
                status="complete",
                summary=(
                    f"Verified {len(results)} claims: "
                    f"{verified} VERIFIED, {uncertain} UNCERTAIN, {contradicted} CONTRADICTED."
                    + (" (Ensemble mode)" if is_high_stakes else "")
                ),
                detail={
                    "total_claims": len(results),
                    "verified": verified,
                    "uncertain": uncertain,
                    "contradicted": contradicted,
                    "ensemble_mode": is_high_stakes,
                    "models_used": [settings.model_verification],
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 7 failed: {e}")
            # Mark all claims uncertain rather than crashing
            state.verification_results = [
                VerificationResult(
                    claim_id=c.claim_id,
                    claim_text=c.claim_text,
                    verdict="UNCERTAIN",
                    confidence=0.0,
                    reasoning=f"Verification stage error: {e}",
                    verifier_model="none",
                )
                for c in state.claims
            ]
            self.log(state, status="failed", summary=f"Verification failed, all marked UNCERTAIN: {e}",
                     started_at=started_at, error=str(e))

        return state
