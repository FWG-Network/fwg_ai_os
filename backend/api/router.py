from fastapi import APIRouter
from backend.core.logger import log

api_router = APIRouter(prefix="/api/v1")


# ─── Safe import helper ───────────────────────────────────────────────
def _include(module_path: str, attr: str = "router") -> None:
    """
    Include a router safely.
    If the module has errors, log warning and skip — server stays up.
    """
    try:
        import importlib
        module = importlib.import_module(module_path)
        router = getattr(module, attr)
        api_router.include_router(router)
        log.info(f"[Router] ✅ {module_path}")
    except Exception as e:
        log.warning(f"[Router] ⚠️ Skipped {module_path}: {e}")


# ─── Core endpoints ───────────────────────────────────────────────────
_include("backend.api.endpoints.discovery")
_include("backend.api.endpoints.feedback")
_include("backend.api.endpoints.ranking")

# ─── AI / LLM endpoints ───────────────────────────────────────────────
_include("backend.api.endpoints.llm")
_include("backend.api.endpoints.multimodal")

# ─── AIOS endpoints ───────────────────────────────────────────────────
_include("backend.api.endpoints.os")

# ─── Future endpoints (safe — won't crash if not ready) ───────────────
_include("backend.api.endpoints.memory")    # vector memory UI
_include("backend.api.endpoints.trends")    # trend dashboard
