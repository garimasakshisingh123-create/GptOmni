"""
backend/services/web_search.py
Serper API wrapper for real-time web search.
Runs multiple queries concurrently and deduplicates by URL.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from urllib.parse import urlparse

import httpx

from backend.config import settings
from backend.models.documents import Document, SearchResult

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"

HIGH_AUTHORITY_DOMAINS = {
    "gov", "edu", "nih.gov", "fda.gov", "who.int",
    "nejm.org", "thelancet.com", "nature.com",
    "pubmed.ncbi.nlm.nih.gov", "cdc.gov", "ecb.europa.eu",
    "federalreserve.gov", "sec.gov", "bbc.com", "reuters.com",
    "apnews.com", "nytimes.com",
}


def _is_high_authority(domain: str) -> bool:
    """Check if a domain is considered high authority."""
    domain = domain.lower().lstrip("www.")
    if any(domain.endswith(f".{tld}") for tld in ["gov", "edu"]):
        return True
    return any(auth in domain for auth in HIGH_AUTHORITY_DOMAINS)


def _extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lstrip("www.")
        return domain
    except Exception:
        return ""


def _result_to_document(result: dict, position: int) -> Document:
    """Convert a Serper organic result dict to a Document."""
    url = result.get("link", "")
    domain = _extract_domain(url)
    return Document(
        doc_id=str(uuid.uuid4()),
        source="web",
        url=url,
        title=result.get("title", ""),
        snippet=result.get("snippet", ""),
        domain=domain,
        published_date=result.get("date"),
        relevance_score=1.0 / (position + 1),  # Simple position-based score pre-rerank
        authority_tag="high" if _is_high_authority(domain) else "standard",
    )


async def search(query: str, num_results: int = 5) -> list[Document]:
    """
    Run a single web search via Serper API.
    
    Returns:
        List of Document objects from organic results
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                SERPER_URL,
                headers={
                    "X-API-KEY": settings.serper_api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": num_results},
            )
            response.raise_for_status()
            data = response.json()

        organic = data.get("organic", [])
        docs = [_result_to_document(r, i) for i, r in enumerate(organic)]
        logger.debug(f"Serper: '{query}' → {len(docs)} results")
        return docs

    except Exception as e:
        logger.error(f"web_search: failed for query '{query}': {e}")
        return []


async def search_all(queries: list[str], num_results: int = 5) -> list[Document]:
    """
    Run all queries concurrently and deduplicate results by URL.
    
    Returns:
        Deduplicated list of Documents from all queries
    """
    results_per_query = await asyncio.gather(
        *[search(q, num_results) for q in queries],
        return_exceptions=True,
    )

    seen_urls: set[str] = set()
    all_docs: list[Document] = []

    for result in results_per_query:
        if isinstance(result, Exception):
            logger.warning(f"web_search: one query failed: {result}")
            continue
        for doc in result:
            if doc.url and doc.url not in seen_urls:
                seen_urls.add(doc.url)
                all_docs.append(doc)

    return all_docs
