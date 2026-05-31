"""
backend/utils/json_parser.py
Safe JSON parser for LLM outputs.
LLMs often wrap JSON in markdown fences or return slightly malformed JSON.
This util strips fences and tries multiple parsing strategies before giving up.
"""

import json
import re
from typing import Any, Optional


def safe_parse_json(text: str) -> Optional[Any]:
    """
    Attempt to parse JSON from LLM output using multiple strategies:
    1. Direct json.loads
    2. Strip markdown code fences (```json ... ```)
    3. Extract first JSON object/array via regex
    4. Return None if all strategies fail
    """
    if not text:
        return None

    text = text.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown fences
    fence_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    match = re.search(fence_pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Extract first JSON object
    obj_match = re.search(r"\{[\s\S]*\}", text)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 4: Extract first JSON array
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        try:
            return json.loads(arr_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def extract_json_array(text: str) -> Optional[list]:
    """Extract a JSON array specifically from text."""
    result = safe_parse_json(text)
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "claims" in result:
        return result["claims"]
    return None
