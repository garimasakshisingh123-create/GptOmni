"""
backend/pipeline/stage_06_generation.py
Stage 6: Output Generation with Reasoning Scaffolds
Calls DeepSeek-R1 with CoT. Extracts <think> block and JSON claims.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from backend.config import settings
from backend.models.pipeline_state import PipelineState
from backend.pipeline.stage import BaseStage
from backend.services import openrouter_client
from backend.utils.claim_extractor import extract_claims_from_text
from backend.utils.json_parser import safe_parse_json

logger = logging.getLogger(__name__)


def _strip_think_block(text: str) -> tuple[str, str]:
    """
    Extract and remove <think>...</think> block from DeepSeek-R1 output.
    Returns (answer_text, think_text).
    """
    think_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)
    match = think_pattern.search(text)

    think_text = ""
    if match:
        think_text = match.group(1).strip()
        text = think_pattern.sub("", text).strip()

    return text, think_text


def _extract_json_claims_block(text: str) -> tuple[str, str]:
    """
    Find and remove the JSON claims array from the generation output.
    Returns (text_without_json, json_string).
    """
    # Look for ```json ... ``` fences first
    fence_match = re.search(r"```json\s*([\s\S]*?)```", text)
    if fence_match:
        json_str = fence_match.group(1).strip()
        clean_text = text[: fence_match.start()].strip()
        return clean_text, json_str

    # Look for raw JSON array starting with [{ pattern
    array_match = re.search(r"(\[\s*\{[\s\S]*\}\s*\])", text)
    if array_match:
        json_str = array_match.group(1)
        clean_text = text[: array_match.start()].strip()
        return clean_text, json_str

    return text, ""


class Stage06Generation(BaseStage):
    stage_number = 6
    stage_name = "Output Generation"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            system_prompt = self.load_prompt("prompts/system/gptomni_base.md")

            # Build the user message: context_block + query + instructions
            context = state.context_block or ""
            reprompt = state.reprompt_template or ""
            query = state.original_query

            user_message = f"{context}\n\n---\n\nUSER QUERY:\n{query}\n\n---\n\nINSTRUCTIONS:\n{reprompt}\n\nThink step by step. Use the evidence. Cite sources. Then output your JSON claims array."

            response = await openrouter_client.chat_completion(
                model=settings.model_generation,
                messages=[{"role": "user", "content": user_message}],
                system=system_prompt,
                temperature=0.3,
                max_tokens=2000,
            )

            # 1. Extract <think> block → reasoning_trace
            response_no_think, think_text = _strip_think_block(response)
            state.reasoning_trace = think_text if think_text else None

            # 2. Extract JSON claims block
            answer_text, json_str = _extract_json_claims_block(response_no_think)
            state.raw_generation = answer_text.strip()

            # 3. Parse claims
            if json_str:
                claims = extract_claims_from_text(json_str, max_claims=settings.pipeline_max_claims)
            else:
                claims = []

            # 4. Fallback: if no claims parsed, try LLM extraction
            if not claims and state.raw_generation:
                logger.info("Stage 6: No claims in generation output, running extraction fallback")
                try:
                    extraction_prompt_template = self.load_prompt("prompts/pipeline/v1_claim_extraction.md")
                    extraction_prompt = (
                        extraction_prompt_template
                        .replace("{{ raw_generation }}", state.raw_generation[:3000])
                        .replace("{{ max_claims }}", str(settings.pipeline_max_claims))
                    )
                    fallback_response = await openrouter_client.chat_completion(
                        model=settings.model_intent,
                        messages=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.0,
                        max_tokens=1024,
                    )
                    claims = extract_claims_from_text(fallback_response, max_claims=settings.pipeline_max_claims)
                except Exception as fe:
                    logger.warning(f"Stage 6: Claim extraction fallback also failed: {fe}")

            state.claims = claims

            word_count = len(state.raw_generation.split()) if state.raw_generation else 0
            think_tokens = len(think_text.split()) if think_text else 0

            self.log(
                state,
                status="complete",
                summary=(
                    f"Generated {len(claims)} claims extracted. "
                    f"Answer: {word_count} words. "
                    f"Reasoning trace: {think_tokens} tokens."
                ),
                detail={
                    "claim_count": len(claims),
                    "answer_words": word_count,
                    "reasoning_tokens": think_tokens,
                    "model_used": settings.model_generation,
                    "claims_preview": [c.claim_text[:80] for c in claims[:3]],
                },
                started_at=started_at,
            )

        except Exception as e:
            logger.error(f"Stage 6 failed: {e}")
            state.raw_generation = f"Generation failed: {e}"
            state.claims = []
            self.log(state, status="failed", summary=f"Generation failed: {e}",
                     started_at=started_at, error=str(e))

        return state
