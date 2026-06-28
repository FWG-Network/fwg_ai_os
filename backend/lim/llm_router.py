"""
backend/lim/llm_router.py
LLM Router — select model + generate response.
Supports: HuggingFace Space Agent, HF Inference API, fallback mock.
"""
from __future__ import annotations

import os
import yaml
from typing import Optional
from backend.core.logger import log


# ── Default routing (fallback if config/models.yml missing) ──────────
DEFAULT_ROUTING = {
    "default":     "HF_AGENT",
    "llm_agent":   "HF_AGENT",
    "summarize":   "HF_AGENT",
    "trend":       "HF_AGENT",
    "rag":         "HF_AGENT",
    "code":        "HF_AGENT",
}


class LLMRouter:
    """
    Routes tasks to appropriate LLM model.
    ✅ Fix: no crash at startup if config missing (uses default)
    ✅ Fix: real generate() method with HuggingFace integration
    """

    def __init__(self, config_path: str = "config/models.yml"):
        self.routing_map = DEFAULT_ROUTING.copy()

        # ✅ Fix: graceful fallback — no crash if file missing
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f) or {}
                if "model_routing" in config:
                    self.routing_map.update(config["model_routing"])
                    log.info(f"[LLMRouter] Loaded config from {config_path}")
            except Exception as e:
                log.warning(f"[LLMRouter] Config load failed: {e} — using defaults")
        else:
            log.warning(f"[LLMRouter] {config_path} not found — using default routing")

    # ── SELECT model ──────────────────────────────────────────────────
    def select(self, task_type: str) -> str:
        """Select LLM model based on task type."""
        return self.routing_map.get(task_type, self.routing_map["default"])

    # ── GENERATE ──────────────────────────────────────────────────────
    async def generate(
        self,
        prompt:     str,
        model:      Optional[str] = None,
        max_tokens: int           = 512,
        task_type:  str           = "default",
    ) -> str:
        """
        Generate LLM response.
        Priority: HuggingFace Space Agent → HF Inference API → mock fallback
        """
        selected = model or self.select(task_type)
        log.info(f"[LLMRouter] generate model={selected} tokens={max_tokens}")

        # ── Option 1: HuggingFace Space Agent (AGENT_URL) ─────────────
        if selected == "HF_AGENT":
            result = await self._call_hf_agent(prompt, max_tokens)
            if result:
                return result

        # ── Option 2: HuggingFace Inference API ───────────────────────
        result = await self._call_hf_inference(prompt, max_tokens)
        if result:
            return result

        # ── Option 3: Fallback mock ───────────────────────────────────
        log.warning("[LLMRouter] All LLM providers failed — returning mock response")
        return f"[Mock LLM] Generated response for: '{prompt[:100]}...'"

    # ── HuggingFace Agent ─────────────────────────────────────────────
    async def _call_hf_agent(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            from backend.core.config import settings
            agent_url = getattr(settings, "AGENT_URL", "")
            hf_token  = getattr(settings, "HF_TOKEN", "")

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
                result = data.get("generated_text") or data.get("response") or data.get("text")
                log.info("[LLMRouter] ✅ HF Agent response received")
                return result

        except Exception as e:
            log.warning(f"[LLMRouter] HF Agent failed: {e}")
            return None

    # ── HuggingFace Inference API ─────────────────────────────────────
    async def _call_hf_inference(self, prompt: str, max_tokens: int) -> Optional[str]:
        try:
            from backend.core.config import settings
            hf_token = getattr(settings, "HF_TOKEN", "")

            if not hf_token:
                return None

            import httpx
            model_id = "mistralai/Mistral-7B-Instruct-v0.2"

            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://api-inference.huggingface.co/models/{model_id}",
                    json={
                        "inputs":      prompt,
                        "parameters": {"max_new_tokens": max_tokens},
                    },
                    headers={"Authorization": f"Bearer {hf_token}"},
                )
                resp.raise_for_status()
                data = resp.json()

                if isinstance(data, list) and data:
                    result = data[0].get("generated_text", "")
                    # Remove input prompt from output
                    if result.startswith(prompt):
                        result = result[len(prompt):].strip()
                    log.info("[LLMRouter] ✅ HF Inference response received")
                    return result

        except Exception as e:
            log.warning(f"[LLMRouter] HF Inference failed: {e}")
            return None


# ── Global instance ───────────────────────────────────────────────────
llm_router = LLMRouter()
