"""
backend/api/endpoints/os.py
═══════════════════════════════════════════════════════════════
  fwg_ai_os — Autonomous OS  |  Fixed v3
  TaskPlanner.create_plan(goal_description, goal_id) → List[TaskModel]
  WorkerClient.health() → async
  DiscoveryEngine.discover() → async
═══════════════════════════════════════════════════════════════
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

# ── Lazy singletons ────────────────────────────────────────────
_task_planner    = None
_discovery_engine = None
_ranking_engine  = None


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


# ── Schemas ────────────────────────────────────────────────────
class OSCommand(BaseModel):
    command: str = Field(..., description="Natural language OS command")
    user_id: str = "system"
    context: Optional[Dict[str, Any]] = None
    async_mode: bool = False


class AgentRunRequest(BaseModel):
    agent: str = Field(..., description="discover | trend | llm")
    input: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "system"


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    collection: str = "fwg_content"


class OSResponse(BaseModel):
    model_config = ConfigDict(exclude_none=True)  # ✅ auto-drop null fields

    status:    str
    task_id:   str | None        = None
    result:    Any | None        = None
    plan:      List[str] | None  = None
    agent:     str | None        = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ── Health helpers (all sync — called via to_thread) ──────────
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
        redis_lib.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=6379, socket_timeout=2,
        ).ping()
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
    # FIX: health() is async — run in new event loop
    try:
        loop = asyncio.new_event_loop()
        health = loop.run_until_complete(worker_client.health())
        loop.close()
        return "online" if health else "degraded"
    except Exception:
        return "offline (async tasks unavailable)"


# ── VERSION A CORE — preserved exactly ────────────────────────
@router.post("/submit_goal", response_model=TaskStatusResponse)
async def submit_autonomous_os_goal(request: TaskRequest):
    """Submits a high-level goal to the Autonomous OS."""
    log.info(f"Autonomous OS: Goal submitted: {request.goal}, User: {request.user_id}")
    try:
        response = await worker_client.submit_task(request)
        return TaskStatusResponse(**response)
    except HTTPException as e:
        log.error(f"Failed to submit Autonomous OS goal to worker: {e.detail}")
        raise e
    except Exception as e:
        log.error(f"Unexpected error submitting Autonomous OS goal: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


@router.get("/task/status/{task_id}", response_model=TaskStatusResponse)
async def get_autonomous_os_task_status(task_id: str):
    """Retrieves the current status of an Autonomous OS task."""
    log.info(f"Autonomous OS: Request for task status: {task_id}")
    try:
        return await worker_client.get_task_status(task_id)
    except HTTPException as e:
        log.error(f"Failed to get Autonomous OS task status from worker: {e.detail}")
        raise e
    except Exception as e:
        log.error(f"Unexpected error getting Autonomous OS task status: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")


# ── VERSION B — fixed to real TaskPlanner interface ────────────
@router.post("/execute", response_model=OSResponse)
async def execute_command(cmd: OSCommand):
    """
    Natural language → create_plan(goal_description, goal_id) → List[TaskModel].
    FIX: create_plan is sync → asyncio.to_thread.
    """
    log.info(f"OS/execute: '{cmd.command}' user={cmd.user_id}")
    planner = _get_planner()
    try:
        task_models = await asyncio.to_thread(
            planner.create_plan,
            cmd.command,    # goal_description
            cmd.user_id,    # goal_id
        )
        steps         = [t.description for t in task_models]
        primary_agent = task_models[0].tool_name if task_models else "unknown"

        if cmd.async_mode:
            task = worker_client.submit_task(
                task_type="os_execute",
                payload={"command": cmd.command, "plan": steps,
                         "user_id": cmd.user_id},
            )
            log.info(f"OS/execute: queued task_id={task.get('task_id')}")
            return OSResponse(status="queued", task_id=task.get("task_id"),
                              plan=steps, agent=primary_agent)

        return OSResponse(
            status="planned",
            result=[{"description": t.description,
                     "tool": t.tool_name,
                     "params": getattr(t, "tool_params", {})}
                    for t in task_models],
            plan=steps,
            agent=primary_agent,
        )
    except Exception as e:
        log.error(f"OS/execute error: {e}")
        raise HTTPException(status_code=500, detail=f"OS execution error: {e}")


@router.post("/plan", response_model=OSResponse)
async def generate_plan(cmd: OSCommand):
    """Dry-run: show plan without executing."""
    log.info(f"OS/plan: '{cmd.command}'")
    try:
        task_models = await asyncio.to_thread(
            _get_planner().create_plan,
            cmd.command,
            cmd.user_id,
        )
        steps = [t.description for t in task_models]
        agent = task_models[0].tool_name if task_models else "unknown"
        return OSResponse(status="planned", plan=steps, agent=agent)
    except Exception as e:
        log.error(f"OS/plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/run", response_model=OSResponse)
async def run_agent(req: AgentRunRequest):
    """
    Run specific agent.
    FIX: discover() is async — await directly.
         trend/llm → route through create_plan.
    """
    log.info(f"OS/agent: agent={req.agent} user={req.user_id}")
    try:
        if req.agent == "discover":
            topic      = req.input.get("topic", "AI trends")
            # FIX: discover is async — await directly
            candidates = await _get_discovery().discover(topic)
            ranked     = await asyncio.to_thread(
                _get_ranking().rank, candidates, req.user_id
            )
            return OSResponse(status="completed",
                              result={"ranked_content": ranked},
                              agent="discover+rank")

        elif req.agent == "trend":
            kw          = req.input.get("keywords", ["AI"])
            keyword_str = kw[0] if kw else "AI"
            task_models = await asyncio.to_thread(
                _get_planner().create_plan,
                f"trend {keyword_str}",
                req.user_id,
            )
            return OSResponse(
                status="completed",
                result=[{"tool": t.tool_name, "desc": t.description}
                        for t in task_models],
                agent="trend_scanner",
            )

        elif req.agent == "llm":
            prompt = req.input.get("prompt", "")
            if not prompt:
                raise HTTPException(status_code=400,
                                    detail="'prompt' required for llm agent")
            task_models = await asyncio.to_thread(
                _get_planner().create_plan, prompt, req.user_id
            )
            return OSResponse(
                status="completed",
                result=[{"tool": t.tool_name, "desc": t.description}
                        for t in task_models],
                agent="llm",
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent '{req.agent}'. Valid: discover | trend | llm",
            )

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"OS/agent {req.agent} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/query", response_model=OSResponse)
async def query_memory(req: MemoryQueryRequest):
    """Vector memory query via TaskPlanner generic research plan."""
    log.info(f"OS/memory: query='{req.query}' top_k={req.top_k}")
    try:
        task_models = await asyncio.to_thread(
            _get_planner().create_plan,
            req.query,
            "memory_query",
        )
        return OSResponse(
            status="completed",
            result={"tasks": [t.description for t in task_models],
                    "query": req.query, "top_k": req.top_k},
            agent="vector_memory",
        )
    except Exception as e:
        log.error(f"OS/memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def system_status():
    """Full health check — all services in parallel."""
    qdrant, db, redis, cel = await asyncio.gather(
        asyncio.to_thread(_ping_qdrant),
        asyncio.to_thread(_ping_db),
        asyncio.to_thread(_ping_redis),
        asyncio.to_thread(_ping_worker),
    )
    services = {
        "qdrant":        qdrant,
        "database":      db,
        "redis":         redis,
        "celery_worker": cel,
        "youtube_api":   "configured" if getattr(settings, "YOUTUBE_API_KEY", "") else "not set",
        "hf_token":      "configured" if getattr(settings, "HF_TOKEN", "") else "not set",
    }
    critical_ok = all("online" in services[s] for s in ["qdrant", "database"])
    any_error   = any("offline" in v for v in services.values())
    overall = ("operational" if (critical_ok and not any_error)
               else ("degraded" if critical_ok else "critical"))
    log.info(f"OS/status: {overall}")
    return {"os": "fwg_ai_os", "version": "1.0.0",
            "status": overall, "services": services,
            "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/reset", response_model=OSResponse)
async def soft_reset():
    """Soft reset: flush Redis + reload singletons."""
    global _task_planner, _discovery_engine, _ranking_engine
    log.info("OS/reset: Soft reset triggered")
    actions = []
    try:
        import redis as redis_lib
        redis_lib.Redis(
            host=getattr(settings, "REDIS_HOST", "localhost"),
            port=6379, socket_timeout=2,
        ).flushdb()
        actions.append("redis_cache_cleared")
    except Exception:
        actions.append("redis_unavailable_skipped")
    _task_planner = _discovery_engine = _ranking_engine = None
    actions.append("service_singletons_reset")
    return OSResponse(status="reset_complete", result={
        "actions": actions,
        "message": "Soft reset done. Services still running.",
    })
