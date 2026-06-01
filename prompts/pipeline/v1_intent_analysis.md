Analyze the following user query and return a JSON classification.

QUERY:
{{ original_query }}

Return ONLY a JSON object with these exact fields:
{
  "intent_type": "<factual|analytical|creative|conversational|code>",
  "needs_web_search": <true|false>,
  "is_high_stakes": <true|false>,
  "claim_types": ["<numeric|temporal|entity|causal|comparative|general>"],
  "domain": "<medicine|finance|law|science|technology|history|geography|general|other>",
  "confidence": <0.0 to 1.0>
}

Definitions:
- intent_type "factual": ANY query asking for facts, information, lists, definitions, data, or events. This includes questions like "What are the Indian states?", "Who is the president?", "List all planets", "How many countries are in Africa?" — all of these are FACTUAL.
- intent_type "analytical": query asks for analysis, comparison, explanation of causes, pros/cons, or reasoning.
- intent_type "creative": query asks to write a story, poem, essay, or creative content.
- intent_type "conversational": ONLY greetings, small talk with zero factual content ("Hi", "Thanks", "How are you", "Tell me a joke").
- intent_type "code": query is about writing, debugging, or explaining code.

CRITICAL RULE: If the query contains ANY of these words, it is FACTUAL not conversational:
- what, who, when, where, which, how many, how much, list, name, tell me, explain, define, describe, what are, what is, why, give me

- needs_web_search: true if the answer benefits from current or specific factual data. For simple general knowledge (capitals, country lists, historical facts), set to true anyway so we can provide citations.
- is_high_stakes: true ONLY if a wrong answer could cause direct harm (medical diagnosis, legal advice, financial decisions).
- claim_types: what categories of verifiable claims the answer will likely contain.
- confidence: your confidence in this classification.

Examples:
- "What are the states of India?" → intent_type: "factual", needs_web_search: true
- "List all US presidents" → intent_type: "factual", needs_web_search: true
- "What is photosynthesis?" → intent_type: "factual", needs_web_search: false
- "Should I buy Tesla stock?" → intent_type: "analytical", is_high_stakes: true
- "Hello!" → intent_type: "conversational", needs_web_search: false
- "Write a poem about rain" → intent_type: "creative", needs_web_search: false

Return ONLY the JSON. No preamble, no explanation.
