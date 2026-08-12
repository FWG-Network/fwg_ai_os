"""
backend/lim/llm_router.py
LLM Router v3 — honest multi-provider fallback chain.

⚠️ STATUS: PROPOSED / UNVERIFIED against live APIs.
Cloudflare Workers AI and GitHub Models endpoint shapes below follow each
provider's publicly documented REST/OpenAI-compatible interface as of this
writing, but have NOT been execution-tested in this environment (no network
egress to those domains here). Verify status codes + response shapes in a
real dev run before treating this as production-ready.

Core rule (Honesty Constraint / Sprint 00.5 Bug #5 fix):
  models.yml NEVER names a specific provider — every task_type is "auto".
  This router is the ONLY place that decides which provider actually gets
  called, and it MUST log the real provider + real model that answered.
  No "logged Claude, actually answered by Mistral" ghost-fallback, ever.
"""
from __future__ import annotations

import os
import yaml
import httpx
from typing import Optional
from backend.core.logger import log
from backend.core.config import settings


# ── task_type -> fallback chain category ────────────────────────────────
# "legacy"  : HF Agent -> HF Inference -> Mock (unchanged core behavior)
# "premium" : GitHub Models -> Cloudflare -> OpenRouter -> Mock
# "writer"  : GitHub Models -> OpenRouter -> Mock (skips Cloudflare —
#             long-form writing needs bigger context / quality than the
#             free Cloudflare tier reliably gives)
# "fast"    : Cloudflare -> OpenRouter -> Mock (skips GitHub Models —
#             bulk/background work, GH Models daily cap saved for
#             high-value calls)
TASK_CATEGORY = {
    "default":   "legacy",
    "llm_agent": "legacy",
    "trend":     "legacy",
    "discovery": "legacy",
    "rag":       "legacy",
    "summarize": "legacy",

    "reasoning": "premium",
    "story":     "premium",

    "writer":    "writer",
    "code":      "writer",
    "creative":  "writer",   # ASSUMPTION — confirm with Dev if this should be "premium" instead

    "fast":      "fast",
}

# task_type -> which GitHub Models model id to request (premium/writer tiers only)
GH_MODEL_BY_TASK = {
    "reasoning": os.getenv("GH_MODEL_REASONING", "o1-mini"),
    "story":     os.getenv("GH_MODEL_STORY", "gpt-4o"),
    "writer":    os.getenv("GH_MODEL_WRITER", "gpt-4o"),
    "code":      os.getenv("GH_MODEL_CODE", "gpt-4o"),
    "creative":  os.getenv("GH_MODEL_CREATIVE", "gpt-4o"),
}

# task_type -> which Cloudflare Workers AI model id to request (premium/fast tiers only)
# NOTE: exact @cf/... catalog ids drift over time — verify against
# https://developers.cloudflare.com/workers-ai/models/ before relying on these.
CF_MODEL_BY_TASK = {
    "reasoning": os.getenv("CF_MODEL_REASONING", "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"),
    "story":     os.getenv("CF_MODEL_STORY", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
    "fast":      os.getenv("CF_MODEL_FAST", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
}

# task_type -> which .env preference var holds the OpenRouter model id
OPENROUTER_PREF_ENV = {
    "reasoning": "MODEL_REASONING",
    "story":     "STORY_MODEL_PREFERENCE",
    "writer":    "MODEL_WRITER",
    "code":      "MODEL_WRITER",
    "creative":  "MODEL_WRITER",
    "fast":      "MODEL_FAST",
}

DEFAULT_ROUTING = {k: "auto" for k in TASK_CATEGORY}


class LLMRouter:
    def __init__(self, config_path: str = "config/models.yml"):
        self.routing_map = DEFAULT_ROUTING.copy()

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
                if "model_routing" in config:
                    loaded = config["model_routing"]
                    non_auto = {k: v for k, v in loaded.items() if v != "auto"}
                    if non_auto:
                        # ✅ Fix (Bug #5 regression guard): models.yml must never
                        # hardcode a provider claim. Refuse to load a violating
                        # entry rather than silently trusting it.
                        log.error(
                            f"[LLMRouter] {config_path} contains non-'auto' entries "
                            f"{non_auto} — ignoring file, using safe defaults. "
                            f"This is a Honesty Constraint violation, fix models.yml."
                        )
                    else:
                        self.routing_map.update(loaded)
                        log.info(f"[LLMRouter] Loaded config from {config_path}")
            except Exception as e:
                log.warning(f"[LLMRouter] Config load failed: {e} — using defaults")
        else:
            log.warning(f"[LLMRouter] {config_path} not found — using default routing")

    def select_category(self, task_type: str) -> str:
        return TASK_CATEGORY.get(task_type, "legacy")

    # ── GENERATE ──────────────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 512,
        task_type: str = "default",
    ) -> str:
        category = self.select_category(task_type)
        log.info(f"[LLMRouter] task_type={task_type} category={category} tokens={max_tokens}")

        if category == "legacy":
            result = await self._call_hf_agent(prompt, max_tokens)
            if result:
                self._log_answered("HF Agent", "HF_AGENT")
                return result
            result = await self._call_hf_inference(prompt, max_tokens)
            if result:
                self._log_answered("HF Inference", "mistralai/Mistral-7B-Instruct-v0.2")
                return result
            return self._mock(prompt)

        if category == "premium":
            result = await self._call_github_models(prompt, max_tokens, GH_MODEL_BY_TASK.get(task_type))
            if result:
                return result
            result = await self._call_cloudflare(prompt, max_tokens, CF_MODEL_BY_TASK.get(task_type))
            if result:
                return result
            result = await self._call_gemini(prompt, max_tokens)
            if result:
                return result
            result = await self._call_openrouter(prompt, max_tokens, task_type)
            if result:
                return result
            return self._mock(prompt)

        if category == "writer":
            result = await self._call_github_models(prompt, max_tokens, GH_MODEL_BY_TASK.get(task_type))
            if result:
                return result
            result = await self._call_gemini(prompt, max_tokens)
            if result:
                return result
            result = await self._call_openrouter(prompt, max_tokens, task_type)
            if result:
                return result
            return self._mock(prompt)

        if category == "fast":
            result = await self._call_cloudflare(prompt, max_tokens, CF_MODEL_BY_TASK.get(task_type))
            if result:
                return result
            result = await self._call_gemini(prompt, max_tokens)
            if result:
                return result
            result = await self._call_openrouter(prompt, max_tokens, task_type)
            if result:
                return result
            return self._mock(prompt)

        # unreachable given TASK_CATEGORY.get default, kept for safety
        log.warning(f"[LLMRouter] Unknown category for task_type={task_type} — falling to mock")
        return self._mock(prompt)

    # ── Honest logging helper ────────────────────────────────────────
    def _log_answered(self, provider: str, model: str) -> None:
        log.info(f"[LLMRouter] Answered by: {provider} -> {model}")

    def _mock(self, prompt: str) -> str:
        log.warning("[LLMRouter] All providers failed/unconfigured — returning mock response")
        self._log_answered("Mock", "none")
        return f"[Mock LLM] Generated response for: '{prompt[:100]}...'"

    # ── GitHub Models (OpenAI-compatible, Azure AI Inference endpoint) ─
    async def _call_github_models(self, prompt: str, max_tokens: int, model_id: Optional[str]) -> Optional[str]:
        token = getattr(settings, "GH_MODELS_TOKEN", "")
        if not token or not model_id:
            return None
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://models.inference.ai.azure.com/chat/completions",
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code == 429:
                    log.warning("[LLMRouter] GitHub Models rate-limited (429) — falling through")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                self._log_answered("GitHub Models", model_id)
                return text
        except Exception as e:
            log.warning(f"[LLMRouter] GitHub Models call failed: {e}")
            return None

    # ── Cloudflare Workers AI ────────────────────────────────────────
    async def _call_cloudflare(self, prompt: str, max_tokens: int, model_id: Optional[str]) -> Optional[str]:
        api_key = getattr(settings, "CLOUDFLARE_API_KEY", "")
        account_id = getattr(settings, "CLOUDFLARE_ACCOUNT_ID", "")
        if not api_key or not account_id or not model_id:
            return None
        try:
            import httpx
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model_id}"
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    url,
                    json={"messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 429:
                    log.warning("[LLMRouter] Cloudflare Workers AI rate-limited (429) — falling through")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data.get("result", {}).get("response")
                if text:
                    self._log_answered("Cloudflare Workers AI", model_id)
                return text
        except Exception as e:
            log.warning(f"[LLMRouter] Cloudflare Workers AI call failed: {e}")
            return None

    # ── Gemini (Google generative AI) ───────────────────────────────
    async def _call_gemini(self, prompt: str, max_tokens: int) -> Optional[str]:
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if not api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": max_tokens},
                    },
                )
                if resp.status_code == 429:
                    log.warning("[LLMRouter] Gemini rate-limited (429) — falling through")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
                if text:
                    self._log_answered("Gemini", "gemini-2.0-flash")
                return text
        except Exception as e:
            log.warning(f"[LLMRouter] Gemini call failed: {e}")
            return None

    # ── OpenRouter (OpenAI-compatible gateway) ───────────────────────
    async def _call_openrouter(self, prompt: str, max_tokens: int, task_type: str) -> Optional[str]:
        api_key = getattr(settings, "OPENROUTER_API_KEY", "")
        env_key = OPENROUTER_PREF_ENV.get(task_type, "OPENROUTER_MODEL")
        model_id = getattr(settings, env_key, None) or getattr(settings, "OPENROUTER_MODEL", "")
        if not api_key or not model_id:
            return None
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={
                        "model": model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                    },
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 429:
                    log.warning("[LLMRouter] OpenRouter rate-limited (429) — falling through")
                    return None
                resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                self._log_answered("OpenRouter", model_id)
                return text
        except Exception as e:
            log.warning(f"[LLMRouter] OpenRouter call failed: {e}")
            return None

    # ── HuggingFace Agent (legacy chain, unchanged) ──────────────────
    async def _call_hf_agent(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            agent_url = getattr(settings, "AGENT_URL", "")
            hf_token = getattr(settings, "HF_TOKEN", "")
            if not agent_url:
                return None
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{agent_url}/generate",
                    json={"prompt": prompt, "max_tokens": max_tokens},
                    headers={"Authorization": f"Bearer {hf_token}"} if hf_token else {},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("generated_text") or data.get("response") or data.get("text")
        except Exception as e:
            log.warning(f"[LLMRouter] HF Agent failed: {e}")
            return None

    # ── HuggingFace Inference (legacy chain, unchanged) ──────────────
    async def _call_hf_inference(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            hf_token = getattr(settings, "HF_TOKEN", "")
            if not hf_token:
                return None
            import httpx
            model_id = "mistralai/Mistral-7B-Instruct-v0.2"
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://api-inference.huggingface.co/models/{model_id}",
                    json={"inputs": prompt, "parameters": {"max_new_tokens": max_tokens}},
                    headers={"Authorization": f"Bearer {hf_token}"},
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and data:
                    result = data[0].get("generated_text", "")
                    if result.startswith(prompt):
                        result = result[len(prompt):].strip()
                    return result
        except Exception as e:
            log.warning(f"[LLMRouter] HF Inference failed: {e}")
            return None


llm_router = LLMRouter()
