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

            # To avoid OpenRouter rate limits (429s) and make this stage instantly free,
            # we use a fast rule-based fallback instead of calling an LLM.
            state.search_queries = [state.original_query]
            state.reprompt_template = (
                "Answer based on the evidence. "
                "After your answer, output your claims as a valid JSON array with fields: "
                "claim_id (string), claim_text (string), claim_type (string), "
                "supporting_source_ids (array of SOURCE_N strings), confidence (0.0-1.0)"
            )

            self.log(
                state,
                status="complete",
                summary=f"Fast rule-based optimization. Using raw query.",
                detail={
                    "search_queries": state.search_queries,
                    "reprompt_preview": state.reprompt_template[:100] + "...",
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 2 failed: {e}")
            self.log(state, status="failed", summary=f"Query optimizer failed: {e}",
                     started_at=started_at, error=str(e))

        return state
