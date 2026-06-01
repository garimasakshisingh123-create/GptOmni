"""
backend/pipeline/stage_05_context.py
Stage 5: Context Construction
Formats reranked documents into a structured EVIDENCE BLOCK for the LLM.
Authority-tagged, source-numbered, ready for faithful citation.
"""

from __future__ import annotations

import logging
from datetime import datetime

from backend.models.documents import Document
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage

logger = logging.getLogger(__name__)

HIGH_AUTHORITY_DOMAINS = {
    "gov", "edu", "nih.gov", "fda.gov", "who.int",
    "nejm.org", "thelancet.com", "nature.com",
    "pubmed.ncbi.nlm.nih.gov", "cdc.gov", "ecb.europa.eu",
    "federalreserve.gov", "sec.gov",
}


def _get_authority_tag(domain: str) -> str:
    domain = domain.lower()
    if any(auth in domain for auth in HIGH_AUTHORITY_DOMAINS):
        return "high authority"
    if domain.endswith(".gov") or domain.endswith(".edu"):
        return "high authority"
    return "standard"


def _build_evidence_block(docs: list[Document], reprompt_template: str) -> str:
    lines = [
        "=== EVIDENCE BLOCK ===",
        "You must base your answer ONLY on the evidence below.",
        "For every factual claim, cite the [SOURCE_N] it comes from.",
        "Do not introduce facts not present in the evidence.",
        "",
    ]

    for i, doc in enumerate(docs, 1):
        authority = _get_authority_tag(doc.domain)
        lines.append(f"[SOURCE_{i}] Title: \"{doc.title}\"")
        lines.append(f"URL: {doc.url}")
        lines.append(f"Domain: {doc.domain} ({authority})")
        if doc.published_date:
            lines.append(f"Date: {doc.published_date}")
        lines.append(f"Content: {doc.snippet}")
        lines.append("")

    lines.append("=== END EVIDENCE BLOCK ===")
    lines.append("")
    if reprompt_template:
        lines.append(reprompt_template)

    return "\n".join(lines)


class Stage05Context(BaseStage):
    stage_number = 5
    stage_name = "Context Construction"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            docs = state.reranked_documents
            reprompt = state.reprompt_template or (
                "After your answer, output your claims as a valid JSON array with fields: "
                "claim_id (string), claim_text (string), claim_type (string), "
                "supporting_source_ids (array of SOURCE_N strings), confidence (0.0-1.0)"
            )

            if not docs:
                # No sources found — instruct the model to answer from training knowledge
                intent_type = state.intent.intent_type if state.intent else "factual"
                state.context_block = (
                    "=== EVIDENCE BLOCK ===\n"
                    "No external sources were retrieved for this query.\n"
                    "You MUST answer this question using your training knowledge.\n"
                    "Be thorough, detailed, and well-structured in your response.\n"
                    "=== END EVIDENCE BLOCK ===\n\n"
                    + reprompt
                )

                token_count = len(state.context_block) // 4
                self.log(
                    state,
                    status="complete",
                    summary="No sources available. Minimal context assembled.",
                    detail={"source_count": 0, "token_estimate": token_count},
                    started_at=started_at,
                )
                return state

            context_block = _build_evidence_block(docs, reprompt)
            state.context_block = context_block

            token_count = len(context_block) // 4
            high_authority_count = sum(
                1 for d in docs if _get_authority_tag(d.domain) == "high authority"
            )

            self.log(
                state,
                status="complete",
                summary=(
                    f"Assembled context from {len(docs)} sources "
                    f"({high_authority_count} high-authority). "
                    f"~{token_count} tokens."
                ),
                detail={
                    "source_count": len(docs),
                    "high_authority_count": high_authority_count,
                    "token_estimate": token_count,
                    "sources": [
                        {
                            "source_id": f"SOURCE_{i + 1}",
                            "url": d.url,
                            "title": d.title,
                            "domain": d.domain,
                            "snippet": d.snippet,
                            "published_date": d.published_date,
                            "authority_tag": d.authority_tag,
                            "claim_ids": [],
                        }
                        for i, d in enumerate(docs)
                    ],
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 5 failed: {e}")
            state.context_block = f"Context assembly failed: {e}"
            self.log(state, status="failed", summary=f"Context assembly failed: {e}",
                     started_at=started_at, error=str(e))

        return state
