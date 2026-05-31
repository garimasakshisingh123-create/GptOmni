The following is an AI-generated response. Extract all factual claims from it as a JSON array.

RESPONSE TEXT:
{{ raw_generation }}

For each factual claim (a specific, verifiable statement of fact), output:
{
  "claim_id": "C<number>",
  "claim_text": "<the exact factual claim as a standalone sentence>",
  "claim_type": "<numeric|temporal|entity|causal|comparative|general>",
  "supporting_source_ids": [],
  "confidence": 0.8
}

Rules:
- Only extract FACTUAL claims (things that can be true or false)
- Do not extract opinions, definitions, or general statements
- Each claim must be self-contained (understandable without context)
- Maximum {{ max_claims }} claims
- Return ONLY the JSON array. No preamble.
