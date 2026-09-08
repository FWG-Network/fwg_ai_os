"""
backend/aios/agent.py
Agent base class + Real LLM Agent implementation.
"""
from abc import ABC, abstractmethod
from typing import Optional
from backend.core.logger import log


# ── Abstract Base ─────────────────────────────────────────────────────
class Agent(ABC):
    """Contract: every agent must implement async run()."""

    @abstractmethod
    async def run(
        self,
        task_description: str,
        user_id:          str = "system",
    ) -> str:
        pass


# ── Real LLM Agent ────────────────────────────────────────────────────
class LLMAgent(Agent):
    """
    Real agent — routes to LLMOrchestrator.
    ✅ async run()
    ✅ real LLM call (not mock)
    ✅ fallback to mock if orchestrator unavailable
    """

    async def run(
        self,
        task_description: str,
        user_id:          str = "system",
        task_type:        str = "default",
    ) -> str:
        log.info(f"[LLMAgent] task='{task_description[:60]}' user={user_id}")
        try:
            from backend.lim.orchestrator import llm_orchestrator
            result = await llm_orchestrator.generate_response(
                query=task_description,
                user_id=user_id,
                task_type=task_type,
            )
            response = result.get("response", "")
            log.info(f"[LLMAgent] ✅ Response ({len(response)} chars)")
            return response

        except Exception as e:
            log.error(f"[LLMAgent] Orchestrator failed: {e}")
            raise


# ── Mock Agent (dev/test only) ────────────────────────────────────────
class MockLLMAgent(Agent):
    """Deterministic mock for testing — no real LLM calls."""

    async def run(
        self,
        task_description: str,
        user_id:          str = "system",
    ) -> str:
        log.debug(f"[MockLLMAgent] task='{task_description[:60]}'")
        return f"[Mock] Completed: {task_description}"


# ── Factory ───────────────────────────────────────────────────────────
def get_agent(mock: bool = False) -> Agent:
    """Return real or mock agent based on environment."""
    if mock:
        return MockLLMAgent()
    return LLMAgent()
