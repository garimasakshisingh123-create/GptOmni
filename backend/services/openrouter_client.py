"""
backend/services/openrouter_client.py
Async OpenRouter API wrapper with retry logic.
All LLM calls in the pipeline go through this single client.
"""

from __future__ import annotations

import logging
import asyncio

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from backend.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "HTTP-Referer": "https://gptomni.app",
    "X-Title": "GptOmni",
    "Content-Type": "application/json",
}


@retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def chat_completion(
    model: str,
    messages: list[dict],
    system: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """
    Call OpenRouter chat completions API.
    
    Args:
        model: OpenRouter model string (e.g. "mistralai/mistral-7b-instruct:free")
        messages: List of {"role": ..., "content": ...} dicts
        system: Optional system prompt (prepended as system message)
        temperature: 0.0 for deterministic, higher for creative
        max_tokens: Maximum tokens in response
    
    Returns:
        Content string of the first choice message
    
    Raises:
        httpx.HTTPStatusError: On 4xx/5xx after retries
    """
    full_messages = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    payload = {
        "model": model,
        "messages": full_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        for attempt in range(5):
            response = await client.post(
                OPENROUTER_API_URL,
                headers=OPENROUTER_HEADERS,
                json=payload,
            )

            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                wait_time = 10.0
                try:
                    data = response.json()
                    error_meta = data.get("error", {}).get("metadata", {})
                    retry_after_meta = error_meta.get("retry_after_seconds")
                    if retry_after_meta is not None:
                        wait_time = float(retry_after_meta)
                    elif retry_after is not None:
                        wait_time = float(retry_after)
                except Exception:
                    pass
                
                wait_time = max(2.0, min(wait_time, 35.0))
                logger.warning(f"OpenRouter rate limit hit (429). Sleeping for {wait_time}s before attempt {attempt+2}/5.")
                await asyncio.sleep(wait_time)
                continue

            response.raise_for_status()
            data = response.json()

            try:
                content = data["choices"][0]["message"]["content"]
                return content or ""
            except (KeyError, IndexError) as e:
                logger.error(f"Unexpected OpenRouter response format: {data}")
                raise ValueError(f"Could not extract content from OpenRouter response: {e}")
        
        # If we reach here, we exhausted 5 attempts due to 429
        raise httpx.HTTPStatusError("Exhausted retries due to rate limits (429)", request=response.request, response=response)
