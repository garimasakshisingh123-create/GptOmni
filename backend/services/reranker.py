"""
backend/services/reranker.py
Singleton CrossEncoder reranker for retrieval quality filtering.
Uses ms-marco-MiniLM-L-6-v2 for accurate relevance scoring.
"""

from __future__ import annotations

import logging

from backend.models.documents import Document

logger = logging.getLogger(__name__)

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_reranker = None


def get_reranker():
    """Lazy singleton — loads model on first call, then caches."""
    global _reranker
    if _reranker is None:
        logger.info(f"Loading reranker model: {MODEL_NAME}")
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(MODEL_NAME)
        logger.info("Reranker model loaded.")
    return _reranker


def rerank(query: str, docs: list[Document], top_k: int = 6) -> list[Document]:
    """
    Rerank documents using cross-encoder relevance scoring.
    
    Args:
        query: Original user query
        docs: Documents to rerank
        top_k: Maximum number of documents to return
    
    Returns:
        Top-k documents sorted by relevance score (highest first)
    """
    if not docs:
        return []

    model = get_reranker()

    # Build (query, snippet) pairs for scoring
    pairs = [(query, doc.snippet) for doc in docs]

    try:
        scores = model.predict(pairs)
    except Exception as e:
        logger.error(f"reranker: prediction failed: {e}")
        return docs[:top_k]

    # Attach scores and sort
    for doc, score in zip(docs, scores):
        doc.relevance_score = float(score)

    sorted_docs = sorted(docs, key=lambda d: d.relevance_score, reverse=True)

    # Quality filter: drop docs with score < -5.0, but always keep at least 3
    SCORE_THRESHOLD = -5.0
    MIN_KEEP = 3

    filtered = [d for d in sorted_docs if d.relevance_score >= SCORE_THRESHOLD]
    if len(filtered) < MIN_KEEP:
        filtered = sorted_docs[:MIN_KEEP]

    # Also drop snippets that are too short (< 50 chars)
    filtered = [d for d in filtered if len(d.snippet.strip()) >= 50]
    if len(filtered) < MIN_KEEP:
        filtered = sorted_docs[:MIN_KEEP]

    return filtered[:top_k]
