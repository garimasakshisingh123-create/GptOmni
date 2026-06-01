"""
backend/pipeline/stage_06_generation.py
Stage 6: Output Generation with Reasoning Scaffolds
Generates a comprehensive, grounded answer using context from Stage 5.
Falls back through model chain if primary model returns too-short or failed output.
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


def _is_answer_too_short(text: str) -> bool:
    """Return True if the answer is suspiciously short (likely a failure)."""
    if not text:
        return True
    words = text.split()
    return len(words) < 30


# Model cascade — try in order until we get a solid answer
# We use a more reliable model first, DeepSeek-R1 as a quality option later
GENERATION_MODEL_CASCADE = [
    "google/gemma-3-27b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-r1:free",
    "google/gemma-3-12b-it:free",
    "qwen/qwen3-14b:free",
]


class Stage06Generation(BaseStage):
    stage_number = 6
    stage_name = "Output Generation"

    async def run(self, state: PipelineState) -> PipelineState:
        started_at = datetime.utcnow()

        try:
            system_prompt = self.load_prompt("prompts/system/gptomni_base.md")

            # Build user message — context block already contains reprompt instruction
            # from Stage 5, so we do NOT repeat the claims instruction here (avoids confusion).
            context = state.context_block or ""
            query = state.original_query

            user_message = (
                f"{context}\n\n"
                f"---\n\n"
                f"USER QUERY:\n{query}\n\n"
                f"---\n\n"
                f"Please provide a comprehensive, well-structured answer. "
                f"Use the evidence above where available. "
                f"Use headers, bullet points, and clear formatting. "
                f"After your answer, output the JSON claims array as instructed."
            )

            answer_text = ""
            think_text = ""
            json_str = ""
            model_used = settings.model_generation

            # Try each model in the cascade until we get a satisfactory answer
            primary = settings.model_generation
            # Build the full cascade starting from config model
            cascade = [primary]
            for m in GENERATION_MODEL_CASCADE:
                if m != primary:
                    cascade.append(m)

            for model in cascade:
                try:
                    logger.info(f"Stage 6: Trying generation model: {model}")
                    response = await openrouter_client.chat_completion(
                        model=model,
                        messages=[{"role": "user", "content": user_message}],
                        system=system_prompt,
                        temperature=0.3,
                        max_tokens=3500,
                    )

                    # 1. Extract <think> block → reasoning_trace
                    response_no_think, think_text_candidate = _strip_think_block(response)
                    # 2. Extract JSON claims block
                    candidate_answer, json_str_candidate = _extract_json_claims_block(response_no_think)

                    if not _is_answer_too_short(candidate_answer):
                        # Good answer — use it
                        answer_text = candidate_answer
                        think_text = think_text_candidate
                        json_str = json_str_candidate
                        model_used = model
                        logger.info(f"Stage 6: Got satisfactory answer from {model} ({len(answer_text.split())} words)")
                        break
                    else:
                        logger.warning(
                            f"Stage 6: Model {model} returned too-short answer "
                            f"({len(candidate_answer.split())} words). Trying next model..."
                        )
                        # Store partial answer in case all models fail
                        if not answer_text or len(candidate_answer) > len(answer_text):
                            answer_text = candidate_answer
                            think_text = think_text_candidate
                            json_str = json_str_candidate
                            model_used = model

                except Exception as e:
                    logger.warning(f"Stage 6: Model {model} failed: {e}. Trying next model...")
                    continue

            if not answer_text:
                # All models failed — give a clear error message
                answer_text = (
                    "I was unable to generate a response at this time due to model availability issues. "
                    "Please try again in a moment."
                )

            state.reasoning_trace = think_text if think_text else None
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
                    f"Model used: {model_used}. "
                    f"Reasoning trace: {think_tokens} tokens."
                ),
                detail={
                    "claim_count": len(claims),
                    "answer_words": word_count,
                    "reasoning_tokens": think_tokens,
                    "model_used": model_used,
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
