class PromptEngine:
    def build(self, system_prompt: str, context: str, query: str) -> str:
        """Builds a structured prompt for the LLM."""
        return f"""
<system_prompt>
{system_prompt}
</system_prompt>

<retrieved_context>
{context}
</retrieved_context>

<user_query>
{query}
</user_query>
"""
