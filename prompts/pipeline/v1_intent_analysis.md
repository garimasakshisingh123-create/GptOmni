Analyze the following user query and return a JSON classification.

QUERY:
{{ original_query }}

Return ONLY a JSON object with these exact fields:
{
  "intent_type": "<factual|analytical|creative|conversational|code>",
  "needs_web_search": <true|false>,
  "is_high_stakes": <true|false>,
  "claim_types": ["<numeric|temporal|entity|causal|comparative>"],
  "domain": "<medicine|finance|law|science|technology|history|general|other>",
  "confidence": <0.0 to 1.0>
}

Definitions:
- intent_type "factual": query is asking for facts, data, or events
- intent_type "analytical": query asks for analysis, comparison, or explanation of causes
- intent_type "conversational": greeting, small talk, or question with no factual claims needed
- intent_type "code": query is about writing or debugging code
- needs_web_search: true if answer depends on current events, recent data, or specific facts
- is_high_stakes: true if wrong answer could cause harm (medical, legal, financial decisions)
- claim_types: what categories of verifiable claims the answer will likely contain
- confidence: your confidence in this classification (0.0 = very uncertain, 1.0 = certain)

Return ONLY the JSON. No preamble, no explanation.
