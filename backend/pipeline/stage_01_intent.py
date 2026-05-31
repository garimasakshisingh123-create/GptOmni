"""
backend/pipeline/stage_01_intent.py
Stage 1: Intent Analysis
Classifies the query to determine pipeline routing.
Conversational queries skip stages 3-7.
Code queries skip verification.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import IntentResult, PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import openrouter_client
from backend.utils.json_parser import safe_parse_json

logger = logging.getLogger(__name__)


class Stage01Intent(BaseStage):
    stage_number = 1
    stage_name = "Intent Analysis"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            prompt_template = self.load_prompt("prompts/pipeline/v1_intent_analysis.md")
            prompt = prompt_template.replace("{{ original_query }}", state.original_query)

            response = await openrouter_client.chat_completion(
                model=settings.model_intent,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=256,
            )

            parsed = safe_parse_json(response)

            if not parsed or not isinstance(parsed, dict):
                logger.warning("Stage 1: Failed to parse intent JSON, using defaults")
                parsed = {
                    "intent_type": "factual",
                    "needs_web_search": True,
                    "is_high_stakes": False,
                    "claim_types": ["general"],
                    "domain": "general",
                    "confidence": 0.5,
                }

            state.intent = IntentResult(
                intent_type=parsed.get("intent_type", "factual"),
                needs_web_search=bool(parsed.get("needs_web_search", True)),
                is_high_stakes=bool(parsed.get("is_high_stakes", False)),
                claim_types=parsed.get("claim_types", ["general"]),
                domain=parsed.get("domain", "general"),
                confidence=float(parsed.get("confidence", 0.5)),
            )

            intent = state.intent
            summary = (
                f"Classified as {intent.intent_type}, "
                f"{'high-stakes' if intent.is_high_stakes else 'normal'}, "
                f"domain: {intent.domain}. "
                f"Claim types: {', '.join(intent.claim_types)}."
            )

            if intent.confidence < 0.6:
                logger.warning(f"Stage 1: Low confidence classification ({intent.confidence:.2f})")

            self.log(
                state,
                status="complete",
                summary=summary,
                detail={
                    "intent_type": intent.intent_type,
                    "needs_web_search": intent.needs_web_search,
                    "is_high_stakes": intent.is_high_stakes,
                    "claim_types": intent.claim_types,
                    "domain": intent.domain,
                    "confidence": intent.confidence,
                    "skip_rag": intent.intent_type in ("conversational",),
                    "skip_verification": intent.intent_type in ("conversational", "code"),
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 1 failed: {e}")
            self.log(state, status="failed", summary=f"Intent analysis failed: {e}",
                     started_at=started_at, error=str(e))
            raise  # Stage 1 failure is critical — abort pipeline

        return state
