"""
backend/lim/orchestrator.py
LLM Orchestrator — plan → route → retrieve → generate.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from backend.core.logger import log


class LLMOrchestrator:
    """
    Central AI brain:
    1. ToolPlanner  → decide which tool handles this query
    2. LLMRouter    → select best LLM model
    3. RAGPipeline  → retrieve context + build prompt
    4. LLMRouter    → generate async response
    """

    def __init__(self):
        # ✅ lazy — no heavy objects at startup
        self._rag     = None
        self._tools   = None
        self._llm     = None

    # ── Lazy singletons ───────────────────────────────────────────────
    @property
    def rag(self):
        if self._rag is None:
            from backend.lim.rag_pipeline import rag_pipeline
            self._rag = rag_pipeline
        return self._rag

    @property
    def tools(self):
        if self._tools is None:
            from backend.lim.tool_planner import ToolPlanner
            self._tools = ToolPlanner()
        return self._tools

    @property
    def llm(self):
        if self._llm is None:
            from backend.lim.llm_router import llm_router
            self._llm = llm_router
        return self._llm

    # ── MAIN ENTRY (async) ────────────────────────────────────────────
    async def generate_response(
        self,
        query:     str,
        user_id:   str   = "system",
        task_type: str   = "default",
        model:     Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full orchestration pipeline.
        ✅ Fix: async — real LLM calls, not print() simulation.
        ✅ Fix: consistent response shape always.
        """
        log.info(f"[Orchestrator] query='{query[:60]}' user={user_id} task={task_type}")

        # ── Step 1: Tool routing decision ─────────────────────────────
        try:
            tool = self.tools.decide(query)
        except Exception as e:
            log.warning(f"[Orchestrator] ToolPlanner failed: {e} → default llm")
            tool = "llm"

        # ── Step 2: Route to external tool if needed ──────────────────
        if tool != "llm":
            log.info(f"[Orchestrator] Routing to tool: {tool}")
            return {
                "status":    "routed",
                "tool":      tool,
                "query":     query,
                "response":  None,
                "model_used": None,
            }

        # ── Step 3: Select LLM model ──────────────────────────────────
        selected_model = model or self.llm.select(task_type)
        log.info(f"[Orchestrator] Selected model: {selected_model}")

        # ── Step 4: RAG — retrieve context + build prompt ─────────────
        system_prompt = (
            f"You are the fwg_ai_os brain. "
            f"Current user: {user_id}. "
            f"Task: {task_type}."
        )

        # ✅ Fix: map task_type → prompt template
        template_map = {
            "trend":      "trend",
            "discovery":  "discovery",
            "rag":        "rag",
            "summarize":  "summarize",
        }
        template = template_map.get(task_type, "default")

        try:
            context       = self.rag._retrieve_context(query)
            final_prompt  = self.rag.prompt_engine.build(
                system_prompt=system_prompt,
                context=context,
                query=query,
                template=template,
            )
        except Exception as e:
            log.warning(f"[Orchestrator] RAG failed: {e} → no context")
            final_prompt = query

        # ── Step 5: Generate via LLM ──────────────────────────────────
        try:
            response = await self.llm.generate(
                prompt=final_prompt,
                model=selected_model,
                task_type=task_type,
            )
            log.info(f"[Orchestrator] ✅ Response generated ({len(response)} chars)")
        except Exception as e:
            log.error(f"[Orchestrator] LLM generation failed: {e}")
            response = f"Generation failed: {e}"

        return {
            "status":                      "generated",
            "tool":                        "llm",
            "model_used":                  selected_model,
            "task_type":                   task_type,
            "query":                       query,
            "response":                    response,
            "retrieved_context_from_memory": True,
        }


# ── Global instance ───────────────────────────────────────────────────
llm_orchestrator = LLMOrchestrator()

# ── Backward compat alias ─────────────────────────────────────────────
LLMOrchestrator_instance = llm_orchestrator
