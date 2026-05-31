"""
backend/pipeline/stage_04_reranking.py
Stage 4: Retrieval Evaluation & Reranking
Uses cross-encoder to rerank and filter documents by relevance quality.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import reranker

logger = logging.getLogger(__name__)


class Stage04Reranking(BaseStage):
    stage_number = 4
    stage_name = "Retrieval Reranking"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            raw_docs = state.raw_documents

            if not raw_docs:
                state.reranked_documents = []
                self.log(
                    state,
                    status="skipped",
                    summary="No documents to rerank.",
                    started_at=started_at,
                )
                return state

            reranked = reranker.rerank(
                query=state.original_query,
                docs=raw_docs,
                top_k=settings.pipeline_rerank_top_k,
            )

            state.reranked_documents = reranked

            dropped = len(raw_docs) - len(reranked)
            top_score = reranked[0].relevance_score if reranked else 0.0

            self.log(
                state,
                status="complete",
                summary=(
                    f"Reranked {len(raw_docs)} documents. "
                    f"Selected top {len(reranked)}, dropped {dropped} low-quality."
                ),
                detail={
                    "input_count": len(raw_docs),
                    "output_count": len(reranked),
                    "dropped_count": dropped,
                    "top_score": round(top_score, 3),
                    "selected_urls": [d.url for d in reranked],
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 4 failed: {e}")
            # Fallback: use raw docs as-is
            state.reranked_documents = state.raw_documents[: settings.pipeline_rerank_top_k]
            self.log(
                state,
                status="failed",
                summary=f"Reranking failed, using unranked docs: {e}",
                started_at=started_at,
                error=str(e),
            )

        return state
