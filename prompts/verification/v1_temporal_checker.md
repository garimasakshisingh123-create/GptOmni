Check the date/time accuracy of the following claim against the provided source data.

CLAIM:
"{{ claim_text }}"

SOURCE DATA:
{% for source in relevant_sources %}
[{{ source.source_id }}] Published: {{ source.date }}
"{{ source.snippet }}"
{% endfor %}

Instructions:
1. Identify all dates, time periods, or temporal references in the claim
2. Find corresponding dates in the source data
3. Check if the dates are consistent (exact match, within acceptable range, or contradictory)
4. Flag anachronisms or impossible timelines

Return JSON:
{
  "verdict": "<VERIFIED|UNCERTAIN|CONTRADICTED>",
  "confidence": <0.0 to 1.0>,
  "claim_date": "<date or period as stated in claim>",
  "source_date": "<date or period found in source, or null>",
  "is_consistent": <true|false|null>,
  "reasoning": "<brief explanation>",
  "supporting_source_ids": ["<SOURCE_N>"]
}

Return ONLY the JSON.
