"""
backend/pipeline/stage_08_postprocessing.py
Stage 8: Post-Processing, Citations & Provenance
Injects inline citations, builds ProvenanceRecord, saves to Supabase.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import PipelineState
from backend.models.provenance import ProvenanceRecord, SourceRef
from backend.pipeline.stage import BaseStage
from backend.services import supabase_client
from backend.utils.provenance_hasher import hash_content

logger = logging.getLogger(__name__)

# Unicode superscript digits for inline citations
SUPERSCRIPTS = ["¹", "²", "³", "⁴", "⁵", "⁶", "⁷", "⁸", "⁹", "¹⁰"]


def _inject_citations(text: str, claims, docs) -> str:
    """
    Replace SOURCE_N references in text with superscript citations.
    Builds a mapping from SOURCE_N → superscript index.
    """
    if not text or not docs:
        return text

    source_to_super = {f"SOURCE_{i + 1}": SUPERSCRIPTS[i] for i in range(min(len(docs), 10))}

    result = text
    for source_id, superscript in source_to_super.items():
        result = result.replace(f"[{source_id}]", f"[{superscript}]")

    return result


def _build_source_refs(docs, verification_results) -> list[SourceRef]:
    """Build SourceRef objects from reranked documents."""
    # Build claim_ids per source
    source_to_claims: dict[str, list[str]] = {}
    for vr in verification_results:
        for sid in vr.supporting_source_ids:
            if sid not in source_to_claims:
                source_to_claims[sid] = []
            source_to_claims[sid].append(vr.claim_id)

    refs = []
    for i, doc in enumerate(docs):
        source_id = f"SOURCE_{i + 1}"
        refs.append(SourceRef(
            source_id=source_id,
            url=doc.url,
            title=doc.title,
            domain=doc.domain,
            snippet=doc.snippet,
            retrieved_at=datetime.utcnow(),
            content_hash=hash_content(doc.snippet),
            claim_ids=source_to_claims.get(source_id, []),
            published_date=doc.published_date,
            authority_tag=doc.authority_tag,
        ))

    return refs


class Stage08Postprocessing(BaseStage):
    stage_number = 8
    stage_name = "Post-Processing"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            docs = state.reranked_documents
            raw_text = state.raw_generation or ""
            verification_results = state.verification_results

            # Inject inline citations
            cited_answer = _inject_citations(raw_text, state.claims, docs)
            state.final_answer = cited_answer

            # Build source refs
            source_refs = _build_source_refs(docs, verification_results)

            # Build verification summary
            verdict_summary = {"VERIFIED": 0, "UNCERTAIN": 0, "CONTRADICTED": 0}
            for vr in verification_results:
                verdict_summary[vr.verdict] = verdict_summary.get(vr.verdict, 0) + 1

            # Collect models used
            models_used = list({
                settings.model_generation,
                settings.model_intent,
                *(vr.verifier_model for vr in verification_results),
            })
            models_used = [m for m in models_used if m and m != "none"]

            # Build provenance record
            provenance = ProvenanceRecord(
                run_id=state.run_id,
                conversation_id=state.conversation_id,
                query_hash=hash_content(state.original_query),
                sources=source_refs,
                verification_summary=verdict_summary,
                models_used=models_used,
                pipeline_version=settings.pipeline_version,
            )
            state.provenance = provenance

            # Save to Supabase
            if state.pipeline_run_id:
                await supabase_client.save_claims(state.pipeline_run_id, state.claims)
                await supabase_client.save_verification_results(state.pipeline_run_id, verification_results)
                await supabase_client.save_provenance(state.pipeline_run_id, provenance)

            self.log(
                state,
                status="complete",
                summary=(
                    f"Provenance saved. {len(source_refs)} sources cited. "
                    f"Query hash: {hash_content(state.original_query)[:8]}..."
                ),
                detail={
                    "cited_sources": len(source_refs),
                    "query_hash": hash_content(state.original_query),
                    "verification_summary": verdict_summary,
                    "models_used": models_used,
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 8 failed: {e}")
            state.final_answer = state.raw_generation or ""
            self.log(state, status="failed", summary=f"Post-processing failed: {e}",
                     started_at=started_at, error=str(e))

        return state
