Check the arithmetic or numeric accuracy of the following claim against the provided source data.

CLAIM:
"{{ claim_text }}"

SOURCE DATA:
{% for source in relevant_sources %}
[{{ source.source_id }}]: "{{ source.snippet }}"
{% endfor %}

Instructions:
1. Extract the specific numbers mentioned in the claim
2. Find the corresponding numbers in the source data
3. Check if they match, and whether any calculations are correct
4. Note unit mismatches (%, $, count, rate, etc.)

Return JSON:
{
  "verdict": "<VERIFIED|UNCERTAIN|CONTRADICTED>",
  "confidence": <0.0 to 1.0>,
  "claim_value": "<the number/stat as stated in the claim>",
  "source_value": "<the number/stat as found in source, or null if not found>",
  "unit_match": <true|false|null>,
  "reasoning": "<brief explanation>",
  "supporting_source_ids": ["<SOURCE_N>"]
}

Return ONLY the JSON.
