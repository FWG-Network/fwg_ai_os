"""
backend/api/endpoints/os.py
Autonomous OS endpoint — Fixed v4
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import TaskRequest, TaskStatusResponse
from backend.services.worker_client import worker_client

router = APIRouter(prefix="/os", tags=["Autonomous OS"])

# ── Lazy singletons ──────────────────────────────────────────
_task_planner     = None
_discovery_engine = None
_ranking_engine   = None


def _get_planner():
    global _task_planner
    if _task_planner is None:
        from backend.aios.task_planner import TaskPlanner
        _task_planner = TaskPlanner()
    return _task_planner


def _get_discovery():
    global _discovery_engine
    if _discovery_engine is None:
        from backend.services.discovery_engine import DiscoveryEngine
        _discovery_engine = DiscoveryEngine()
    return _discovery_engine


def _get_ranking():
    global _ranking_engine
    if _ranking_engine is None:
        from backend.services.ranking_engine import RankingEngine
        _ranking_engine = RankingEngine()
    return _ranking_engine


def _flatten_tasks(staged_plan: List[List[Any]]) -> List[Any]:
    """Flatten staged TaskModel lists for endpoint response serialization.

    TaskPlanner's canonical contract remains List[List[TaskModel]].
    """
    return [
        task
        for stage in staged_plan
        for task in stage
    ]


# ── Schemas ───────────────────────────────────────────────────
class OSCommand(BaseModel):
    command:    str                      = Field(..., description="Natural language OS command")
    user_id:    str                      = "system"
    context:    Optional[Dict[str, Any]] = None
    async_mode: bool                     = False


class AgentRunRequest(BaseModel):
    agent:   str            = Field(..., description="discover | trend | llm")
    input:   Dict[str, Any] = Field(default_factory=dict)
    user_id: str            = "system"


class MemoryQueryRequest(BaseModel):
    query:      str
    top_k:      int = Field(default=5, ge=1, le=20)
    collection: str = "fwg_content"


class OSResponse(BaseModel):
    model_config = ConfigDict(exclude_none=True)

    status:    str
    task_id:   Optional[str] = None
    result:    Optional[Any] = None
    plan:      Optional[List[str]] = None
    agent:     Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Health helpers ───────────────────────────────────────────
def _ping_qdrant() -> str:
    try:
        from qdrant_client import QdrantClient
        QdrantClient(
            host=getattr(settings, "QDRANT_HOST", "localhost"),
            port=getattr(settings, "QDRANT_PORT", 6333),
            timeout=3,
        ).get_collections()
        return "online"
    except Exception:
        return "offline"


def _ping_redis() -> str:
    try:
        import redis as redis_lib
        # ✅ Fix: use REDIS_URL (consistent with other services)
        r = redis_lib.from_url(settings.REDIS_URL, socket_timeout=2)
        r.ping()
        return "online"
    except Exception:
        return "offline (personalization degraded)"


def _ping_db() -> str:
    try:
        from sqlalchemy import text
        from backend.models.db import engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "online"
    except Exception:
        return "offline"


def _ping_worker() -> str:
    try:
        import httpx
        resp = httpx.get(
            f"http://{settings.WORKER_HOST}:{settings.WORKER_PORT}/health",
            timeout=3,
        )
        return "online" if resp.status_code == 200 else "degraded"
    except Exception:
        return "offline (async tasks unavailable)"


# ── Core endpoints ────────────────────────────────────────────
@router.post("/submit_goal", response_model=TaskStatusResponse)
async def submit_autonomous_os_goal(request: TaskRequest):
    """Submit high-level goal to Autonomous OS."""
    log.info(f"[OS] Goal: '{request.goal}' user={request.user_id}")
    try:
        response = await worker_client.submit_task(request)
        return TaskStatusResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"[OS] submit_goal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Get status of an OS task."""
    try:
        return await worker_client.get_task_status(task_id)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"[OS] task_status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=OSResponse)
async def execute_command(cmd: OSCommand):
    """Natural language → create_plan → execute."""
    log.info(f"[OS] execute: '{cmd.command}' user={cmd.user_id}")
    planner = _get_planner()
    try:
        staged_plan = await asyncio.to_thread(
            planner.create_plan,
            cmd.command,
            cmd.user_id,
        )
        task_models = _flatten_tasks(staged_plan)

        steps         = [t.description for t in task_models]
        primary_agent = task_models[0].tool_name if task_models else "unknown"

        if cmd.async_mode:
            # ✅ Fix 1: await submit_task
            task = await worker_client.submit_task(
                TaskRequest(goal=cmd.command, user_id=cmd.user_id)
            )
            return OSResponse(
                status="queued",
                task_id=task.get("task_id"),
                plan=steps,
                agent=primary_agent,
            )

        return OSResponse(
            status="planned",
            result=[{
                "description": t.description,
                "tool":        t.tool_name,
                "params":      getattr(t, "tool_params", {}),
            } for t in task_models],
            plan=steps,
            agent=primary_agent,
        )
    except Exception as e:
        log.error(f"[OS] execute error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plan", response_model=OSResponse)
async def generate_plan(cmd: OSCommand):
    """Dry-run: show plan without executing."""
    log.info(f"[OS] plan: '{cmd.command}'")
    try:
        staged_plan = await asyncio.to_thread(
            _get_planner().create_plan,
            cmd.command,
            cmd.user_id,
        )
        task_models = _flatten_tasks(staged_plan)

        steps = [t.description for t in task_models]
        agent = task_models[0].tool_name if task_models else "unknown"
        return OSResponse(status="planned", plan=steps, agent=agent)
    except Exception as e:
        log.error(f"[OS] plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/run", response_model=OSResponse)
async def run_agent(req: AgentRunRequest):
    """Run specific agent: discover | trend | llm."""
    log.info(f"[OS] agent={req.agent} user={req.user_id}")
    try:
        if req.agent == "discover":
            topic      = req.input.get("topic", "AI trends")
            candidates = await _get_discovery().discover(topic)
            # ✅ rank() is sync
            ranked     = _get_ranking().rank(candidates, user_id=req.user_id)
            return OSResponse(
                status="completed",
                result={"ranked_content": ranked, "total": len(ranked)},
                agent="discover+rank",
            )

        elif req.agent == "trend":
            kw      = req.input.get("keywords", ["AI"])
            keyword = kw[0] if kw else "AI"
            staged_plan = await asyncio.to_thread(
                _get_planner().create_plan,
                f"trend {keyword}",
                req.user_id,
            )
            tasks = _flatten_tasks(staged_plan)
            return OSResponse(
                status="completed",
                result=[{"tool": t.tool_name, "desc": t.description} for t in tasks],
                agent="trend_scanner",
            )

        elif req.agent == "llm":
            prompt = req.input.get("prompt", "")
            if not prompt:
                raise HTTPException(400, "'prompt' required for llm agent")
            staged_plan = await asyncio.to_thread(
                _get_planner().create_plan, prompt, req.user_id
            )
            tasks = _flatten_tasks(staged_plan)
            return OSResponse(
                status="completed",
                result=[{"tool": t.tool_name, "desc": t.description} for t in tasks],
                agent="llm",
            )

        raise HTTPException(400, f"Unknown agent '{req.agent}'. Use: discover | trend | llm")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"[OS] agent {req.agent} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/query", response_model=OSResponse)
async def query_memory(req: MemoryQueryRequest):
    """Vector memory query."""
    log.info(f"[OS] memory query='{req.query}' top_k={req.top_k}")
    try:
        from backend.lim.vector_memory import vector_memory_service
        results = await asyncio.to_thread(
            vector_memory_service.search,
            req.query,
            req.top_k,
            req.collection,
        )
        return OSResponse(
            status="completed",
            result={"results": results, "query": req.query, "top_k": req.top_k},
            agent="vector_memory",
        )
    except Exception as e:
        log.error(f"[OS] memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def system_status():
    """Full health check — all services in parallel."""
    qdrant, db, redis_status, worker = await asyncio.gather(
        asyncio.to_thread(_ping_qdrant),
        asyncio.to_thread(_ping_db),
        asyncio.to_thread(_ping_redis),
        asyncio.to_thread(_ping_worker),
    )
    services = {
        "qdrant":        qdrant,
        "database":      db,
        "redis":         redis_status,
        "celery_worker": worker,
        "youtube_api":   "configured" if getattr(settings, "YOUTUBE_API_KEY", "") else "not set",
        "hf_token":      "configured" if getattr(settings, "HF_TOKEN", "")     else "not set",
    }
    critical_ok = all("online" in services[s] for s in ["qdrant", "database"])
    any_offline = any("offline" in v for v in services.values())
    overall     = ("operational" if (critical_ok and not any_offline)
                   else ("degraded" if critical_ok else "critical"))

    log.info(f"[OS] status: {overall}")
    return {
        "os":        "fwg_ai_os",
        "version":   "1.0.0",
        "status":    overall,
        "services":  services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/reset", response_model=OSResponse)
async def soft_reset():
    """Soft reset: flush discovery cache (db=2) only — preserves personalization."""
    global _task_planner, _discovery_engine, _ranking_engine
    log.info("[OS] Soft reset triggered")
    actions = []
    try:
        import redis as redis_lib
        # ✅ Fix 2: flush db=2 (discovery cache) ONLY
        # db=0 = personalization (preserve!)
        # db=2 = discovery cache (safe to flush)
        r = redis_lib.from_url(settings.REDIS_URL, db=2, socket_timeout=2)
        r.flushdb()
        actions.append("discovery_cache_cleared (db=2)")
    except Exception:
        actions.append("redis_unavailable_skipped")

    _task_planner    = _discovery_engine = _ranking_engine = None
    actions.append("service_singletons_reset")

    return OSResponse(
        status="reset_complete",
        result={
            "actions":   actions,
            "preserved": ["personalization_data (db=0)", "user_profiles"],
            "message":   "Soft reset done. User data preserved.",
        },
    )
