"""
backend/services/embedder.py
Singleton SentenceTransformer embedder.
Loads all-MiniLM-L6-v2 once at startup and reuses for all requests.
"""

from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_embedder = None


def get_embedder():
    """Lazy singleton — loads model on first call, then caches."""
    global _embedder
    if _embedder is None:
        logger.info(f"Loading embedder model: {MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer(MODEL_NAME)
        logger.info("Embedder model loaded.")
    return _embedder


def embed(text: str) -> list[float]:
    """
    Embed a single text string.
    
    Returns:
        384-dimensional float list
    """
    model = get_embedder()
    embedding = model.encode(text, convert_to_tensor=False)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts efficiently in a single batch.
    
    Returns:
        List of 384-dimensional float lists
    """
    if not texts:
        return []
    model = get_embedder()
    embeddings = model.encode(texts, convert_to_tensor=False, batch_size=32)
    return [e.tolist() for e in embeddings]
