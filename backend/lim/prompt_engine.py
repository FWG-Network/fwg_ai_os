"""
backend/lim/prompt_engine.py
Prompt Engine — build structured prompts for different task types.
"""
from typing import Optional


class PromptEngine:
    """
    Builds structured prompts for LLM calls.
    Supports multiple templates per task type.
    """

    # ── Templates ─────────────────────────────────────────────────────
    TEMPLATES = {

        "default": """\
<system_prompt>
{system_prompt}
</system_prompt>

<retrieved_context>
{context}
</retrieved_context>

<user_query>
{query}
</user_query>""",

        "trend": """\
<system_prompt>
{system_prompt}
You are analyzing trending content. Focus on engagement signals and virality patterns.
</system_prompt>

<trend_context>
{context}
</trend_context>

<analysis_request>
{query}
</analysis_request>

Provide: 1) Key trend signals 2) Emerging creators 3) Recommended actions.""",

        "discovery": """\
<system_prompt>
{system_prompt}
You are a content discovery AI. Identify high-potential creators and topics.
</system_prompt>

<market_context>
{context}
</market_context>

<discovery_goal>
{query}
</discovery_goal>

Provide: Creator recommendations, content gaps, growth opportunities.""",

        "rag": """\
<system_prompt>
{system_prompt}
Answer using ONLY the retrieved context below. If the context is insufficient, say so.
</system_prompt>

<retrieved_context>
{context}
</retrieved_context>

<question>
{query}
</question>

Answer based on the context above:""",

        "summarize": """\
<system_prompt>
{system_prompt}
</system_prompt>

<content_to_summarize>
{context}
</content_to_summarize>

<instruction>
{query}
</instruction>

Summary:""",
    }

    def build(
        self,
        system_prompt: str,
        context:       str,
        query:         str,
        template:      str = "default",
    ) -> str:
        """
        Build structured prompt from template.
        Falls back to default if template not found.
        """
        # Input validation
        system_prompt = system_prompt.strip() or "You are a helpful AI assistant."
        context       = context.strip()       or "No context available."
        query         = query.strip()         or "No query provided."

        tmpl = self.TEMPLATES.get(template, self.TEMPLATES["default"])

        return tmpl.format(
            system_prompt=system_prompt,
            context=context,
            query=query,
        )
