import pytest

from backend.lim.llm_router import LLMRouter


def test_task_category_contract():
    router = LLMRouter()

    assert router.select_category("default") == "legacy"
    assert router.select_category("reasoning") == "premium"
    assert router.select_category("story") == "premium"
    assert router.select_category("writer") == "writer"
    assert router.select_category("fast") == "fast"
    assert router.select_category("unknown_task") == "legacy"


@pytest.mark.asyncio
async def test_premium_route_reaches_openrouter(monkeypatch):
    router = LLMRouter()
    calls = []

    async def fail_github(prompt, max_tokens, model_id):
        calls.append("github")
        return None

    async def fail_cloudflare(prompt, max_tokens, model_id):
        calls.append("cloudflare")
        return None

    async def fail_gemini(prompt, max_tokens):
        calls.append("gemini")
        return None

    async def real_openrouter(prompt, max_tokens, task_type):
        calls.append(("openrouter", task_type))
        return "REAL-ROUTER-TEST-RESPONSE"

    monkeypatch.setattr(router, "_call_github_models", fail_github)
    monkeypatch.setattr(router, "_call_cloudflare", fail_cloudflare)
    monkeypatch.setattr(router, "_call_gemini", fail_gemini)
    monkeypatch.setattr(router, "_call_openrouter", real_openrouter)

    result = await router.generate(
        "test prompt",
        task_type="reasoning",
    )

    assert result == "REAL-ROUTER-TEST-RESPONSE"
    assert calls == [
        "github",
        "cloudflare",
        "gemini",
        ("openrouter", "reasoning"),
    ]


@pytest.mark.asyncio
async def test_all_real_providers_failed_must_not_return_mock(monkeypatch):
    router = LLMRouter()

    async def fail(*args, **kwargs):
        return None

    def forbidden_mock(prompt):
        pytest.fail("PRODUCTION MOCK FALLBACK WAS CALLED")

    monkeypatch.setattr(router, "_call_github_models", fail)
    monkeypatch.setattr(router, "_call_cloudflare", fail)
    monkeypatch.setattr(router, "_call_gemini", fail)
    monkeypatch.setattr(router, "_call_openrouter", fail)
    monkeypatch.setattr(router, "_mock", forbidden_mock)

    with pytest.raises(Exception):
        await router.generate(
            "test prompt",
            task_type="reasoning",
        )


@pytest.mark.asyncio
async def test_legacy_provider_failure_must_not_return_mock(monkeypatch):
    router = LLMRouter()

    async def fail(*args, **kwargs):
        return None

    def forbidden_mock(prompt):
        pytest.fail("LEGACY PRODUCTION MOCK FALLBACK WAS CALLED")

    monkeypatch.setattr(router, "_call_hf_agent", fail)
    monkeypatch.setattr(router, "_call_hf_inference", fail)
    monkeypatch.setattr(router, "_mock", forbidden_mock)

    with pytest.raises(Exception):
        await router.generate(
            "test prompt",
            task_type="default",
        )
