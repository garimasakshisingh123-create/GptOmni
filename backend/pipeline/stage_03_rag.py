"""
backend/pipeline/stage_03_rag.py
Stage 3: Constant RAG
Runs web search (Serper) + vector DB search (pgvector) concurrently.
Always retrieves external evidence — never trusts model memory alone.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from backend.config import settings
from backend.models.documents import Document
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import embedder, web_search
from backend.services import supabase_client
from backend.utils.provenance_hasher import hash_content

logger = logging.getLogger(__name__)


class Stage03RAG(BaseStage):
    stage_number = 3
    stage_name = "Constant RAG"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            intent = state.intent

            # Skip RAG for purely conversational queries
            if intent and intent.intent_type == "conversational":
                state.raw_documents = []
                self.log(
                    state,
                    status="skipped",
                    summary="Skipped — conversational query needs no retrieval.",
                    started_at=started_at,
                )
                return state

            web_docs: list[Document] = []
            vector_docs: list[Document] = []

            async def do_web_search():
                if intent and intent.intent_type in ("conversational", "code"):
                    return []
                return await web_search.search_all(state.search_queries)

            async def do_vector_search():
                query_embedding = embedder.embed(state.original_query)
                raw_results = await supabase_client.vector_search(
                    query_embedding,
                    top_k=5,
                    threshold=0.3,
                )
                docs = []
                for r in raw_results:
                    docs.append(Document(
                        doc_id=str(r.get("id", uuid.uuid4())),
                        source="vector_db",
                        url=r.get("url", ""),
                        title=r.get("title", ""),
                        snippet=r.get("chunk_text", ""),
                        domain=r.get("domain", ""),
                        published_date=r.get("published_date"),
                        relevance_score=float(r.get("similarity", 0.0)),
                    ))
                return docs

            # Gather both concurrently
            results = await asyncio.gather(
                do_web_search(),
                do_vector_search(),
                return_exceptions=True,
            )

            if isinstance(results[0], Exception):
                logger.warning(f"Stage 3: Web search failed: {results[0]}")
                web_docs = []
            else:
                web_docs = results[0]

            if isinstance(results[1], Exception):
                logger.warning(f"Stage 3: Vector search failed: {results[1]}")
                vector_docs = []
            else:
                vector_docs = results[1]

            # Merge and deduplicate by URL
            seen_urls: set[str] = set()
            all_docs: list[Document] = []

            for doc in web_docs + vector_docs:
                if doc.url and doc.url not in seen_urls:
                    seen_urls.add(doc.url)
                    all_docs.append(doc)
                elif not doc.url:
                    all_docs.append(doc)  # Vector DB chunks may not have unique URLs

            state.raw_documents = all_docs[: settings.pipeline_max_retrieved_docs]

            self.log(
                state,
                status="complete",
                summary=(
                    f"Retrieved {len(web_docs)} web results + {len(vector_docs)} vector DB results. "
                    f"{len(state.raw_documents)} total after deduplication."
                ),
                detail={
                    "web_count": len(web_docs),
                    "vector_count": len(vector_docs),
                    "total_after_dedup": len(state.raw_documents),
                    "search_queries_used": state.search_queries,
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 3 failed: {e}")
            state.raw_documents = []  # Continue with empty docs
            self.log(
                state,
                status="failed",
                summary=f"RAG retrieval failed — continuing with no sources: {e}",
                started_at=started_at,
                error=str(e),
            )
            # Non-critical: continue pipeline

        return state
