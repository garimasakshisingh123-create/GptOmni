"""
backend/services/openrouter_client.py
Async OpenRouter API wrapper with retry logic and fallback model chains.
All LLM calls in the pipeline go through this single client.
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {settings.openrouter_api_key}",
    "HTTP-Referer": "https://gptomni.app",
    "X-Title": "GptOmni",
    "Content-Type": "application/json",
}

# ---------------------------------------------------------------------------
# Fallback model chains
# When the primary model fails (model unavailable / overloaded / returns an
# error body), these chains are tried in order.
# ---------------------------------------------------------------------------
_FALLBACK_CHAINS: dict[str, list[str]] = {
    # Intent & arithmetic: small/fast models
    "meta-llama/llama-3.2-3b-instruct:free": [
        "liquid/lfm-2.5-1.2b-instruct:free",
        "openai/gpt-oss-20b:free",
        "google/gemma-4-26b-a4b-it:free",
    ],
    # Generation: large reliable models — gemma-4-31b is primary
    "google/gemma-4-31b-it:free": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
        "openai/gpt-oss-120b:free",
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "nvidia/nemotron-3-super-120b-a12b:free",
    ],
    # DeepSeek-R1 (if someone manually tries to use it)
    "deepseek/deepseek-r1:free": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemma-4-31b-it:free",
    ],
    # Verification: mid-size instruction models
    "openai/gpt-oss-20b:free": [
        "google/gemma-4-31b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen3-next-80b-a3b-instruct:free",
    ],
}


class OpenRouterError(Exception):
    """Raised when OpenRouter returns an application-level error (200 body with error key)."""


def _get_fallbacks(model: str) -> list[str]:
    """Return fallback model list for the given primary model."""
    # Try exact match first, then prefix match
    if model in _FALLBACK_CHAINS:
        return _FALLBACK_CHAINS[model]
    for key, chain in _FALLBACK_CHAINS.items():
        if model.startswith(key.split(":")[0]):
            return chain
    # Generic fallback for unknown models
    return [
        "meta-llama/llama-3.2-3b-instruct:free",
        "liquid/lfm-2.5-1.2b-instruct:free",
        "google/gemma-4-26b-a4b-it:free",
    ]


async def _call_model(
    client: httpx.AsyncClient,
    model: str,
    full_messages: list[dict],
    temperature: float,
    max_tokens: int,
    max_attempts: int = 5,
) -> str:
    """
    Try a single model up to max_attempts times, handling 429 rate limits
    and application-level error bodies.
    Raises OpenRouterError if the model returns an error body after retries.
    Raises httpx.HTTPStatusError on HTTP-level errors.
    """
    payload = {
        "model": model,
        "messages": full_messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    for attempt in range(max_attempts):
        response = await client.post(
            OPENROUTER_API_URL,
            headers=OPENROUTER_HEADERS,
            json=payload,
        )

        # ── 429 rate limit ────────────────────────────────────────────────
        if response.status_code == 429:
            logger.warning(f"[OpenRouter] Rate limit 429 on {model}. Waiting 3s before fallback to avoid global rate limit ban.")
            await asyncio.sleep(3.0)
            raise OpenRouterError(f"Rate limited (429) on {model}")

        # ── HTTP-level errors (5xx, 4xx except 429) ───────────────────────
        response.raise_for_status()
        data = response.json()

        # ── Application-level error body (200 OK but {"error": ...}) ──────
        if "error" in data and "choices" not in data:
            error_info = data["error"]
            error_code = error_info.get("code", "unknown") if isinstance(error_info, dict) else "unknown"
            error_msg = error_info.get("message", str(error_info)) if isinstance(error_info, dict) else str(error_info)
            logger.warning(
                f"[OpenRouter] Model {model} returned application error "
                f"(code={error_code}): {error_msg}"
            )
            # Treat provider errors / model-unavailable as retriable
            retriable_codes = {
                "model_not_found", "model_unavailable", "provider_error",
                "no_providers_available", "context_length_exceeded", 503, 529,
            }
            if error_code in retriable_codes or (isinstance(error_code, int) and error_code >= 500):
                if attempt < max_attempts - 1:
                    wait = min(4.0 * (attempt + 1), 30.0)
                    logger.warning(f"[OpenRouter] Retrying {model} after {wait}s...")
                    await asyncio.sleep(wait)
                    continue
            raise OpenRouterError(
                f"Model {model} error (code={error_code}): {error_msg}"
            )

        # ── Successful response ───────────────────────────────────────────
        try:
            content = data["choices"][0]["message"]["content"]
            return content or ""
        except (KeyError, IndexError) as e:
            logger.error(f"[OpenRouter] Unexpected response format from {model}: {data}")
            raise OpenRouterError(
                f"Could not extract content from OpenRouter response for {model}: {e}"
            )

    # Exhausted all attempts for this model
    raise OpenRouterError(f"Exhausted {max_attempts} attempts for model {model} due to rate limits.")


async def chat_completion(
    model: str,
    messages: list[dict],
    system: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
) -> str:
    """
    Call OpenRouter chat completions API with automatic fallback model chaining.

    Args:
        model: Primary OpenRouter model string (e.g. "mistralai/mistral-7b-instruct:free")
        messages: List of {"role": ..., "content": ...} dicts
        system: Optional system prompt (prepended as system message)
        temperature: 0.0 for deterministic, higher for creative
        max_tokens: Maximum tokens in response

    Returns:
        Content string of the first choice message

    Raises:
        ValueError: If all models in the fallback chain fail
    """
    full_messages: list[dict] = []
    if system:
        full_messages.append({"role": "system", "content": system})
    full_messages.extend(messages)

    models_to_try = [model] + _get_fallbacks(model)

    async with httpx.AsyncClient(timeout=150.0) as client:
        last_error: Exception = RuntimeError("No models tried.")
        for idx, current_model in enumerate(models_to_try):
            if idx > 0:
                logger.warning(
                    f"[OpenRouter] Falling back to {current_model} "
                    f"(attempt {idx + 1}/{len(models_to_try)})."
                )
            try:
                result = await _call_model(
                    client=client,
                    model=current_model,
                    full_messages=full_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if idx > 0:
                    logger.info(f"[OpenRouter] Fallback succeeded with {current_model}.")
                return result
            except (OpenRouterError, httpx.HTTPStatusError, httpx.TimeoutException) as e:
                logger.warning(f"[OpenRouter] Model {current_model} failed: {e}")
                last_error = e
                continue

    raise ValueError(
        f"All OpenRouter models failed. Last error: {last_error}. "
        f"Models tried: {models_to_try}"
    )
