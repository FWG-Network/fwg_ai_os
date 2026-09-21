from types import SimpleNamespace

import pytest

from backend.lim.orchestrator import LLMOrchestrator


class StubLLM:
    def select(self, task_type):
        return "test-model"

    async def generate(self, **kwargs):
        return "generated response"


def make_orchestrator(rag):
    orchestrator = LLMOrchestrator()
    orchestrator._tools = SimpleNamespace(
        decide=lambda query: "llm",
    )
    orchestrator._rag = rag
    orchestrator._llm = StubLLM()
    return orchestrator


@pytest.mark.asyncio
async def test_generate_response_propagates_real_llm_failure():
    orchestrator = LLMOrchestrator()

    orchestrator._tools = SimpleNamespace(
        decide=lambda query: "llm",
    )

    orchestrator._rag = SimpleNamespace(
        retrieve_context=lambda query: (
            "No relevant context found in memory.",
            False,
        ),
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


@pytest.mark.asyncio
async def test_explicit_task_type_bypasses_tool_planner():
    calls = []

    orchestrator = make_orchestrator(
        SimpleNamespace(
            retrieve_context=lambda query: (
                "No relevant context found in memory.",
                False,
            ),
            prompt_engine=SimpleNamespace(
                build=lambda **kwargs: kwargs["query"],
            ),
        )
    )

    orchestrator._tools = SimpleNamespace(
        decide=lambda query: calls.append(query) or "summarize",
    )

    result = await orchestrator.generate_response(
        query="Draft final summary report for 'Reply with exactly: FWG_DOCTOR_DEEP_E2E_OK'",
        user_id="test-user",
        task_type="writer",
    )

    assert calls == []
    assert result["response"] == "generated response"
    assert result["task_type"] == "writer"


@pytest.mark.asyncio
async def test_retrieved_context_metadata_true_when_memory_returns_hits():
    orchestrator = make_orchestrator(
        SimpleNamespace(
            retrieve_context=lambda query: ("[1] (score=0.900) real context", True),
            prompt_engine=SimpleNamespace(
                build=lambda **kwargs: kwargs["query"],
            ),
        )
    )

    result = await orchestrator.generate_response(
        query="test query",
        user_id="test-user",
        task_type="reasoning",
    )

    assert result["retrieved_context_from_memory"] is True


@pytest.mark.asyncio
async def test_retrieved_context_metadata_false_when_memory_has_no_hits():
    orchestrator = make_orchestrator(
        SimpleNamespace(
            retrieve_context=lambda query: (
                "No relevant context found in memory.",
                False,
            ),
            prompt_engine=SimpleNamespace(
                build=lambda **kwargs: kwargs["query"],
            ),
        )
    )

    result = await orchestrator.generate_response(
        query="test query",
        user_id="test-user",
        task_type="reasoning",
    )

    assert result["retrieved_context_from_memory"] is False


@pytest.mark.asyncio
async def test_retrieved_context_metadata_false_when_rag_retrieval_fails():
    def failing_retrieve(query):
        raise RuntimeError("qdrant unavailable")

    orchestrator = make_orchestrator(
        SimpleNamespace(
            retrieve_context=failing_retrieve,
            prompt_engine=SimpleNamespace(
                build=lambda **kwargs: kwargs["query"],
            ),
        )
    )

    result = await orchestrator.generate_response(
        query="test query",
        user_id="test-user",
        task_type="reasoning",
    )

    assert result["retrieved_context_from_memory"] is False
