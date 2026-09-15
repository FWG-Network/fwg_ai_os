from types import SimpleNamespace

import pytest

from backend.lim.orchestrator import LLMOrchestrator


@pytest.mark.asyncio
async def test_generate_response_propagates_real_llm_failure():
    orchestrator = LLMOrchestrator()

    orchestrator._tools = SimpleNamespace(
        decide=lambda query: "llm",
    )

    orchestrator._rag = SimpleNamespace(
        _retrieve_context=lambda query: "No relevant context found in memory.",
        prompt_engine=SimpleNamespace(
            build=lambda **kwargs: kwargs["query"],
        ),
    )

    class FailingLLM:
        def select(self, task_type):
            return "real-provider-model"

        async def generate(self, **kwargs):
            raise RuntimeError("real provider unavailable")

    orchestrator._llm = FailingLLM()

    with pytest.raises(RuntimeError, match="real provider unavailable"):
        await orchestrator.generate_response(
            query="test query",
            user_id="test-user",
            task_type="reasoning",
        )
