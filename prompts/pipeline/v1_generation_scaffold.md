{{ gptomni_base_system_prompt }}

---

{{ context_block }}

---

USER QUERY:
{{ original_query }}

---

INSTRUCTIONS:
{{ reprompt_template }}

Think step by step. Use the evidence. Cite sources. Then output your JSON claims array.
