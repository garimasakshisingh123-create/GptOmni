"""
backend/services/supabase_client.py
Singleton Supabase client using service role key (bypasses RLS).
All database writes from the backend pipeline go through this client.
Uses supabase-py v2.5.x synchronous client — all DB calls are sync,
wrapped in run_in_executor where needed by async pipeline stages.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from supabase import create_client, Client

from backend.config import settings
from backend.models.claims import Claim, VerificationResult
from backend.models.provenance import ProvenanceRecord, SourceRef

logger = logging.getLogger(__name__)

_client: Optional[Client] = None


def get_client() -> Client:
    """Lazy singleton Supabase client."""
    global _client
    if _client is None:
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _client


# ── Chat ──────────────────────────────────────────────────────────────────────

async def save_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
    run_id: Optional[str] = None,
) -> Optional[str]:
    """Save a chat message. Returns the new message ID."""
    try:
        client = get_client()
        data = {
            "conversation_id": conversation_id,
            "user_id": user_id,
            "role": role,
            "content": content,
        }
        if run_id:
            data["run_id"] = run_id
        result = client.table("messages").insert(data).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.error(f"supabase: save_message failed: {e}")
        return None


async def get_conversation_messages(conversation_id: str) -> list[dict]:
    """Fetch all messages for a conversation, ordered by created_at."""
    try:
        client = get_client()
        result = (
            client.table("messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("created_at")
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"supabase: get_conversation_messages failed: {e}")
        return []


async def create_conversation(user_id: str, title: str = "New Conversation") -> Optional[str]:
    """Create a new conversation. Returns the conversation ID."""
    try:
        client = get_client()
        result = (
            client.table("conversations")
            .insert({"user_id": user_id, "title": title})
            .execute()
        )
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.error(f"supabase: create_conversation failed: {e}")
        return None


async def get_conversations(user_id: str) -> list[dict]:
    """Fetch all conversations for a user, newest first."""
    try:
        client = get_client()
        result = (
            client.table("conversations")
            .select("*")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        logger.error(f"supabase: get_conversations failed: {e}")
        return []


async def update_conversation_title(conversation_id: str, title: str) -> None:
    """Update a conversation title (e.g. based on first message)."""
    try:
        client = get_client()
        client.table("conversations").update({"title": title}).eq("id", conversation_id).execute()
    except Exception as e:
        logger.error(f"supabase: update_conversation_title failed: {e}")


# ── Pipeline Runs ─────────────────────────────────────────────────────────────

async def save_pipeline_run(
    run_id: str,
    conversation_id: str,
    user_id: str,
    original_query: str,
    query_hash: str,
) -> Optional[str]:
    """Create a pipeline_runs row. Returns the row ID."""
    try:
        client = get_client()
        result = (
            client.table("pipeline_runs")
            .insert({
                "id": run_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "original_query": original_query,
                "query_hash": query_hash,
                "status": "running",
            })
            .execute()
        )
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        logger.error(f"supabase: save_pipeline_run failed: {e}")
        return None


async def update_pipeline_run_status(
    run_id: str,
    status: str,
    total_duration_ms: Optional[int] = None,
    intent_result: Optional[dict] = None,
    search_queries: Optional[list] = None,
    models_used: Optional[list] = None,
) -> None:
    """Update pipeline run status and metadata on completion."""
    try:
        client = get_client()
        data: dict = {
            "status": status,
            "completed_at": datetime.utcnow().isoformat(),
        }
        if total_duration_ms is not None:
            data["total_duration_ms"] = total_duration_ms
        if intent_result:
            data["intent_result"] = intent_result
        if search_queries:
            data["search_queries"] = search_queries
        if models_used:
            data["models_used"] = models_used
        client.table("pipeline_runs").update(data).eq("id", run_id).execute()
    except Exception as e:
        logger.error(f"supabase: update_pipeline_run_status failed: {e}")


async def save_stage_log(run_id: str, stage: dict) -> None:
    """Save a single stage log entry."""
    try:
        client = get_client()
        client.table("stage_logs").insert({
            "run_id": run_id,
            "stage_number": stage.get("stage_number"),
            "stage_name": stage.get("stage_name"),
            "status": stage.get("status"),
            "summary": stage.get("summary"),
            "detail": stage.get("detail", {}),
            "duration_ms": stage.get("duration_ms"),
            "error": stage.get("error"),
        }).execute()
    except Exception as e:
        logger.error(f"supabase: save_stage_log failed: {e}")


# ── Claims & Verification ─────────────────────────────────────────────────────

async def save_claims(run_id: str, claims: list[Claim]) -> None:
    """Save extracted claims for a run."""
    if not claims:
        return
    try:
        client = get_client()
        rows = [
            {
                "run_id": run_id,
                "claim_id": c.claim_id,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "confidence": c.confidence,
                "source_ids": c.supporting_source_ids,
            }
            for c in claims
        ]
        client.table("claims").insert(rows).execute()
    except Exception as e:
        logger.error(f"supabase: save_claims failed: {e}")


async def save_verification_results(run_id: str, results: list[VerificationResult]) -> None:
    """Save verification results for a run."""
    if not results:
        return
    try:
        client = get_client()
        rows = [
            {
                "run_id": run_id,
                "claim_id": r.claim_id,
                "verdict": r.verdict,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "supporting_text": r.supporting_text,
                "contradicting_text": r.contradicting_text,
                "supporting_source_ids": r.supporting_source_ids,
                "verifier_model": r.verifier_model,
            }
            for r in results
        ]
        client.table("verification_results").insert(rows).execute()
    except Exception as e:
        logger.error(f"supabase: save_verification_results failed: {e}")


async def save_provenance(run_id: str, provenance: ProvenanceRecord) -> None:
    """Save the full provenance record for a run."""
    try:
        client = get_client()
        client.table("provenance_records").insert({
            "run_id": run_id,
            "sources": [
                {
                    "source_id": s.source_id,
                    "url": s.url,
                    "title": s.title,
                    "domain": s.domain,
                    "snippet": s.snippet,
                    "retrieved_at": s.retrieved_at.isoformat(),
                    "content_hash": s.content_hash,
                    "claim_ids": s.claim_ids,
                    "published_date": s.published_date,
                    "authority_tag": s.authority_tag,
                }
                for s in provenance.sources
            ],
            "verification_summary": provenance.verification_summary,
            "models_used": provenance.models_used,
            "pipeline_version": provenance.pipeline_version,
        }).execute()
    except Exception as e:
        logger.error(f"supabase: save_provenance failed: {e}")


# ── Vector Search ─────────────────────────────────────────────────────────────

async def vector_search(
    query_embedding: list[float],
    top_k: int = 5,
    threshold: float = 0.3,
) -> list[dict]:
    """
    Run pgvector cosine similarity search using match_documents function.
    Returns raw dicts from Supabase.
    """
    try:
        client = get_client()
        result = client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_threshold": threshold,
                "match_count": top_k,
            },
        ).execute()
        return result.data or []
    except Exception as e:
        logger.error(f"supabase: vector_search failed: {e}")
        return []


async def save_document_chunks(chunks_data: list[dict]) -> None:
    """Save document chunks to the vector store."""
    if not chunks_data:
        return
    try:
        client = get_client()
        client.table("documents").insert(chunks_data).execute()
    except Exception as e:
        logger.error(f"supabase: save_document_chunks failed: {e}")
