"""
backend/pipeline/orchestrator.py
The pipeline orchestrator — runs all 9 stages in sequence, emitting SSE events.
This is the core of GptOmni: what gets called on every user message.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage_01_intent import Stage01Intent
from backend.pipeline.stage_02_query_optimizer import Stage02QueryOptimizer
from backend.pipeline.stage_03_rag import Stage03RAG
from backend.pipeline.stage_04_reranking import Stage04Reranking
from backend.pipeline.stage_05_context import Stage05Context
from backend.pipeline.stage_06_generation import Stage06Generation
from backend.pipeline.stage_07_verification import Stage07Verification
from backend.pipeline.stage_08_postprocessing import Stage08Postprocessing
from backend.pipeline.stage_09_delivery import Stage09Delivery
from backend.services import supabase_client
from backend.utils.provenance_hasher import hash_content

logger = logging.getLogger(__name__)


def sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _build_final_payload(state: PipelineState) -> dict:
    """Build the complete 'done' SSE event payload."""
    total_ms = None
    if state.total_start_ms:
        total_ms = int((time.time() - state.total_start_ms) * 1000)

    return {
        "run_id": state.run_id,
        "final_answer": state.final_answer or state.raw_generation or "",
        "stage_logs": [
            {
                "stage_number": log.stage_number,
                "stage_name": log.stage_name,
                "status": log.status,
                "summary": log.summary,
                "detail": log.detail,
                "duration_ms": log.duration_ms,
                "error": log.error,
            }
            for log in state.stage_logs
        ],
        "sources": [
            {
                "source_id": s.source_id,
                "url": s.url,
                "title": s.title,
                "domain": s.domain,
                "snippet": s.snippet,
                "published_date": s.published_date,
                "content_hash": s.content_hash,
                "claim_ids": s.claim_ids,
                "authority_tag": s.authority_tag,
            }
            for s in (state.provenance.sources if state.provenance else [])
        ],
        "claims": [
            {
                "claim_id": c.claim_id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "confidence": c.confidence,
                "supporting_source_ids": c.supporting_source_ids,
            }
            for c in state.claims
        ],
        "verification_results": [
            {
                "claim_id": vr.claim_id,
                "claim_text": vr.claim_text,
                "verdict": vr.verdict,
                "confidence": vr.confidence,
                "reasoning": vr.reasoning,
                "supporting_text": vr.supporting_text,
                "contradicting_text": vr.contradicting_text,
                "supporting_source_ids": vr.supporting_source_ids,
                "verifier_model": vr.verifier_model,
            }
            for vr in state.verification_results
        ],
        "provenance": {
            "run_id": state.provenance.run_id,
            "query_hash": state.provenance.query_hash,
            "verification_summary": state.provenance.verification_summary,
            "models_used": state.provenance.models_used,
            "pipeline_version": state.provenance.pipeline_version,
            "created_at": state.provenance.created_at.isoformat(),
        } if state.provenance else None,
        "total_duration_ms": total_ms,
    }


async def run_pipeline(
    query: str,
    conversation_id: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """
    Main pipeline entry point. Yields SSE event strings.
    Called by the /api/chat endpoint.
    """
    state = PipelineState(
        conversation_id=conversation_id,
        user_id=user_id,
        original_query=query,
    )
    state.total_start_ms = time.time()

    # Create pipeline_runs row in Supabase
    run_db_id = await supabase_client.save_pipeline_run(
        run_id=state.run_id,
        conversation_id=conversation_id,
        user_id=user_id,
        original_query=query,
        query_hash=hash_content(query),
    )
    state.pipeline_run_id = run_db_id

    # Save the user message
    await supabase_client.save_message(
        conversation_id=conversation_id,
        user_id=user_id,
        role="user",
        content=query,
    )

    # Instantiate all 9 stages
    stages = [
        Stage01Intent(),
        Stage02QueryOptimizer(),
        Stage03RAG(),
        Stage04Reranking(),
        Stage05Context(),
        Stage06Generation(),
        Stage07Verification(),
        Stage08Postprocessing(),
        Stage09Delivery(),
    ]

    # Run each stage, emitting SSE events
    for stage in stages:
        # Emit "running" event
        yield sse_event("stage_update", {
            "stage_number": stage.stage_number,
            "stage_name": stage.stage_name,
            "status": "running",
        })

        try:
            state = await stage.run(state)

            # Get the log for this stage
            stage_log = next(
                (log for log in reversed(state.stage_logs) if log.stage_number == stage.stage_number),
                None,
            )

            yield sse_event("stage_update", {
                "stage_number": stage.stage_number,
                "stage_name": stage.stage_name,
                "status": stage_log.status if stage_log else "complete",
                "summary": stage_log.summary if stage_log else "",
                "detail": stage_log.detail if stage_log else {},
                "duration_ms": stage_log.duration_ms if stage_log else None,
            })

            # After stage 6 (generation), stream the answer as tokens
            if stage.stage_number == 6 and state.final_answer is None:
                # Emit the raw generation as a single token event
                # (full streaming would require refactoring to use OpenRouter streaming)
                if state.raw_generation:
                    yield sse_event("token", {"text": state.raw_generation})

        except Exception as e:
            logger.error(f"Pipeline stage {stage.stage_number} raised: {e}")
            yield sse_event("stage_update", {
                "stage_number": stage.stage_number,
                "stage_name": stage.stage_name,
                "status": "failed",
                "error": str(e),
            })

            # Stages 1 and 2 are critical — abort on failure
            if stage.stage_number <= 2:
                logger.error("Critical stage failed — aborting pipeline")
                yield sse_event("done", {
                    "run_id": state.run_id,
                    "final_answer": f"Pipeline failed at stage {stage.stage_number}: {e}",
                    "stage_logs": [],
                    "sources": [],
                    "claims": [],
                    "verification_results": [],
                    "provenance": None,
                    "total_duration_ms": None,
                    "error": str(e),
                })
                return

    # Emit the final answer token after stage 8 post-processing
    if state.final_answer:
        yield sse_event("token", {"text": state.final_answer})

    # Emit the done event with full Intelligence Engine payload
    yield sse_event("done", _build_final_payload(state))
