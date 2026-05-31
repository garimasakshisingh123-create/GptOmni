Verify the following claim against the provided source snippets.

CLAIM TO VERIFY:
"{{ claim_text }}"
Claim type: {{ claim_type }}

SOURCE SNIPPETS:
{% for source in relevant_sources %}
[{{ source.source_id }}] {{ source.title }} ({{ source.domain }}, {{ source.date }})
"{{ source.snippet }}"

{% endfor %}

Return a JSON object:
{
  "verdict": "<VERIFIED|UNCERTAIN|CONTRADICTED>",
  "confidence": <0.0 to 1.0>,
  "reasoning": "<1-2 sentences explaining your verdict>",
  "supporting_text": "<exact phrase from a source that supports the claim, or null>",
  "contradicting_text": "<exact phrase from a source that contradicts the claim, or null>",
  "supporting_source_ids": ["<SOURCE_N>", "..."]
}

Verdict criteria:
- VERIFIED: A source explicitly and directly confirms the claim. confidence >= 0.7
- CONTRADICTED: A source explicitly states something incompatible with the claim
- UNCERTAIN: No source clearly confirms or denies, evidence is ambiguous, or you're unsure

Be strict. Do not mark VERIFIED unless the source is explicit.
Return ONLY the JSON. No preamble.
