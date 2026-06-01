"""
backend/pipeline/stage_02_query_optimizer.py
Stage 2: Query Optimizer
Converts the original query into 3-5 targeted search queries
and generates a reprompt_template for Stage 6.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import openrouter_client
from backend.utils.json_parser import safe_parse_json

logger = logging.getLogger(__name__)


class Stage02QueryOptimizer(BaseStage):
    stage_number = 2
    stage_name = "Query Optimizer"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            intent = state.intent

            # Conversational queries don't need search query generation
            if intent and intent.intent_type == "conversational":
                state.search_queries = []
                state.reprompt_template = (
                    "Answer conversationally. Be helpful and concise. "
                    "After your answer, output an empty JSON claims array: []"
                )
                self.log(
                    state,
                    status="skipped",
                    summary="Skipped — conversational query needs no search queries.",
                    started_at=started_at,
                )
                return state

            prompt_template = self.load_prompt("prompts/pipeline/v1_query_optimizer.md")
            prompt = (
                prompt_template
                .replace("{{ original_query }}", state.original_query)
                .replace("{{ intent_type }}", intent.intent_type if intent else "factual")
                .replace("{{ domain }}", intent.domain if intent else "general")
                .replace("{{ claim_types }}", ", ".join(intent.claim_types) if intent else "general")
                .replace("{{ needs_web_search }}", str(intent.needs_web_search) if intent else "true")
            )

            response = await openrouter_client.chat_completion(
                model=settings.model_intent,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=512,
            )

            parsed = safe_parse_json(response)

            if not parsed or not isinstance(parsed, dict):
                logger.warning("Stage 2: Failed to parse query optimizer JSON, using fallback")
                state.search_queries = [state.original_query]
                state.reprompt_template = (
                    "Answer based on the evidence. "
                    "After your answer, output your claims as a valid JSON array with fields: "
                    "claim_id (string), claim_text (string), claim_type (string), "
                    "supporting_source_ids (array of SOURCE_N strings), confidence (0.0-1.0)"
                )
            else:
                queries = parsed.get("search_queries", [state.original_query])
                state.search_queries = [q for q in queries if q][:5]  # Max 5 queries
                reprompt = parsed.get(
                    "reprompt_template",
                    "After your answer, output your claims as a valid JSON array with fields: "
                    "claim_id (string), claim_text (string), claim_type (string), "
                    "supporting_source_ids (array of SOURCE_N strings), confidence (0.0-1.0)"
                )
                if isinstance(reprompt, str) and ("search_queries" in reprompt or "claim_slots" in reprompt or reprompt.startswith("{")):
                    reprompt = (
                        "After your answer, output your claims as a valid JSON array with fields: "
                        "claim_id (string), claim_text (string), claim_type (string), "
                        "supporting_source_ids (array of SOURCE_N strings), confidence (0.0-1.0)"
                    )
                state.reprompt_template = reprompt

            self.log(
                state,
                status="complete",
                summary=f"Generated {len(state.search_queries)} search queries.",
                detail={
                    "search_queries": state.search_queries,
                    "reprompt_preview": state.reprompt_template[:100] + "..." if state.reprompt_template else "",
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 2 failed: {e}")
            # Non-critical fallback — use original query as search query
            state.search_queries = [state.original_query]
            state.reprompt_template = (
                "After your answer, output your claims as a valid JSON array with fields: "
                "claim_id (string), claim_text (string), claim_type (string), "
                "supporting_source_ids (array), confidence (0.0-1.0)"
            )
            self.log(state, status="failed", summary=f"Query optimizer failed, using fallback: {e}",
                     started_at=started_at, error=str(e))
            # Do NOT re-raise — fallback is good enough to continue the pipeline

        return state
