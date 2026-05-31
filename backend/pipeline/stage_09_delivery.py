"""
backend/pipeline/stage_09_delivery.py
Stage 9: Delivery
Saves final assistant message to Supabase.
Updates pipeline_runs status to "complete".
Builds final SSE "done" payload.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import supabase_client

logger = logging.getLogger(__name__)


class Stage09Delivery(BaseStage):
    stage_number = 9
    stage_name = "Delivery"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            # Calculate total pipeline duration
            total_ms = None
            if state.total_start_ms:
                total_ms = int((time.time() - state.total_start_ms) * 1000)

            # Save assistant message to Supabase
            final_answer = state.final_answer or state.raw_generation or "No response generated."
            if state.conversation_id and state.user_id:
                msg_id = await supabase_client.save_message(
                    conversation_id=state.conversation_id,
                    user_id=state.user_id,
                    role="assistant",
                    content=final_answer,
                    run_id=state.run_id,
                )

                # Update conversation title if this is the first message
                # (title = first 60 chars of user query)
                if state.original_query:
                    title = state.original_query[:60]
                    await supabase_client.update_conversation_title(
                        state.conversation_id, title
                    )

            # Update pipeline_runs status
            if state.pipeline_run_id:
                await supabase_client.update_pipeline_run_status(
                    run_id=state.pipeline_run_id,
                    status="complete",
                    total_duration_ms=total_ms,
                    intent_result={
                        "intent_type": state.intent.intent_type,
                        "is_high_stakes": state.intent.is_high_stakes,
                        "domain": state.intent.domain,
                    } if state.intent else None,
                    search_queries=state.search_queries,
                    models_used=[settings.model_generation, settings.model_intent, settings.model_verification],
                )

            total_s = f"{total_ms / 1000:.1f}s" if total_ms else "unknown"

            self.log(
                state,
                status="complete",
                summary=(
                    f"Delivered. Total: {total_s}. "
                    f"IE payload: {len(state.stage_logs)} stages, "
                    f"{len(state.reranked_documents)} sources, "
                    f"{len(state.claims)} claims."
                ),
                detail={
                    "total_duration_ms": total_ms,
                    "source_count": len(state.reranked_documents),
                    "claim_count": len(state.claims),
                    "verification_count": len(state.verification_results),
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 9 failed: {e}")
            self.log(state, status="failed", summary=f"Delivery failed: {e}",
                     started_at=started_at, error=str(e))

        return state
