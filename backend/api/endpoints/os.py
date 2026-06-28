"""
backend/api/endpoints/os.py
═══════════════════════════════════════════════════════════════
  fwg_ai_os — Autonomous OS  |  Merged: A style + B features
═══════════════════════════════════════════════════════════════
  Endpoints:
    POST  /os/submit_goal          – Submit high-level goal (Version A core)
    GET   /os/task/status/{id}     – Task status            (Version A core)
    POST  /os/execute              – Natural language → agents
    POST  /os/plan                 – Dry-run: generate plan only
    POST  /os/agent/run            – Run specific agent directly
    POST  /os/memory/query         – Query Qdrant vector memory
    GET   /os/status               – Full system health check
    POST  /os/reset                – Soft reset caches
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import TaskRequest, TaskStatusResponse
from backend.services.worker_client import worker_client

router = APIRouter(prefix="/os", tags=["Autonomous OS"])

_task_planner = None
_discovery_engine = None
_ranking_engine = None


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


class OSCommand(BaseModel):
    command: str = Field(..., description="Natural language OS command")
    user_id: str = "system"
    context: Optional[Dict[str, Any]] = None
    async_mode: bool = False


class AgentRunRequest(BaseModel):
    agent: str = Field(..., description="discover | search | memory | trend | llm | parallel")
    input: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "system"


class MemoryQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    collection: str = "fwg_content"


class OSResponse(BaseModel):
    status: str
    task_id: Optional[str] = None
    result: Optional[Any] = None
    plan: Optional[List[str]] = None
    agent: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


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
    try:
        health = worker_client.health()
        return "online" if health else "degraded"
    except Exception:
        return "offline (async tasks unavailable)"


@router.post("/submit_goal", response_model=TaskStatusResponse)
async def submit_autonomous_os_goal(request: TaskRequest):
    """Submits a high-level goal to the Autonomous OS for planning and execution."""
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


@router.post("/execute", response_model=OSResponse)
async def execute_command(cmd: OSCommand):
    """Natural language command -> TaskPlanner -> agents."""
    log.info(f"OS/execute: '{cmd.command}' user={cmd.user_id} async={cmd.async_mode}")
    planner = _get_planner()
    try:
        plan = await planner.create_plan(
            intent=cmd.command,
            context=cmd.context or {},
            user_id=cmd.user_id,
        )
        steps: List[str] = getattr(plan, "steps", [])
        agent: str = getattr(plan, "primary_agent", "unknown")

        if cmd.async_mode:
            task = worker_client.submit_task(
                task_type="os_execute",
                payload={"command": cmd.command, "plan": steps,
                         "user_id": cmd.user_id, "context": cmd.context},
            )
            log.info(f"OS/execute: queued task_id={task.get('task_id')}")
            return OSResponse(status="queued", task_id=task.get("task_id"),
                              plan=steps, agent=agent)

        result = await planner.execute_plan(plan)
        return OSResponse(status="completed", result=result, plan=steps, agent=agent)

    except Exception as e:
        log.error(f"OS/execute error: {e}")
        raise HTTPException(status_code=500, detail=f"OS execution error: {e}")


@router.post("/plan", response_model=OSResponse)
async def generate_plan(cmd: OSCommand):
    """Dry-run: generate execution plan without running it."""
    log.info(f"OS/plan: '{cmd.command}'")
    try:
        plan = await _get_planner().create_plan(
            intent=cmd.command, context=cmd.context or {}, user_id=cmd.user_id,
        )
        return OSResponse(
            status="planned",
            plan=getattr(plan, "steps", []),
            agent=getattr(plan, "primary_agent", "unknown"),
        )
    except Exception as e:
        log.error(f"OS/plan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/run", response_model=OSResponse)
async def run_agent(req: AgentRunRequest):
    """Run a specific AIOS agent directly."""
    log.info(f"OS/agent: agent={req.agent} user={req.user_id}")
    planner = _get_planner()
    try:
        if req.agent == "discover":
            topic = req.input.get("topic", "AI trends")
            candidates = await _get_discovery().discover(topic)
            ranked = await _get_ranking().rank(candidates, req.user_id)
            return OSResponse(status="completed",
                              result={"ranked_content": ranked}, agent="discover+rank")

        elif req.agent == "search":
            result = await planner.run_agent("web_search", req.input)
            return OSResponse(status="completed", result=result, agent="search")

        elif req.agent == "memory":
            result = await planner.run_agent("vector_memory", {
                "query": req.input.get("query", ""),
                "top_k": req.input.get("top_k", 5),
                "collection": req.input.get("collection", "fwg_content"),
            })
            return OSResponse(status="completed", result=result, agent="memory")

        elif req.agent == "trend":
            result = await planner.run_agent("trend_scanner",
                                             {"keywords": req.input.get("keywords", [])})
            return OSResponse(status="completed", result=result, agent="trend")

        elif req.agent == "llm":
            prompt = req.input.get("prompt", "")
            if not prompt:
                raise HTTPException(status_code=400, detail="'prompt' required for llm agent")
            result = await planner.run_agent("llm_agent", {"prompt": prompt})
            return OSResponse(status="completed", result=result, agent="llm")

        elif req.agent == "parallel":
            query = req.input.get("query", "")
            search_r, memory_r = await asyncio.gather(
                planner.run_agent("web_search", {"query": query}),
                planner.run_agent("vector_memory", {"query": query, "top_k": 5}),
                return_exceptions=True,
            )
            return OSResponse(status="completed", result={
                "web_search": search_r if not isinstance(search_r, Exception) else str(search_r),
                "vector_memory": memory_r if not isinstance(memory_r, Exception) else str(memory_r),
            }, agent="parallel(search+memory)")

        else:
            raise HTTPException(status_code=400,
                detail=f"Unknown agent '{req.agent}'. Valid: discover|search|memory|trend|llm|parallel")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"OS/agent {req.agent} error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/query", response_model=OSResponse)
async def query_memory(req: MemoryQueryRequest):
    """Direct Qdrant vector memory query."""
    log.info(f"OS/memory: query='{req.query}' top_k={req.top_k}")
    try:
        result = await _get_planner().run_agent("vector_memory", {
            "query": req.query, "top_k": req.top_k, "collection": req.collection,
        })
        return OSResponse(status="completed", result=result, agent="vector_memory")
    except Exception as e:
        log.error(f"OS/memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def system_status():
    """Full health check: all OS services in parallel."""
    qdrant, db, redis, cel = await asyncio.gather(
        asyncio.to_thread(_ping_qdrant),
        asyncio.to_thread(_ping_db),
        asyncio.to_thread(_ping_redis),
        asyncio.to_thread(_ping_worker),
    )
    services = {
        "qdrant": qdrant, "database": db,
        "redis": redis, "celery_worker": cel,
        "youtube_api": "configured" if getattr(settings, "YOUTUBE_API_KEY", "") else "not set",
        "hf_token":    "configured" if getattr(settings, "HF_TOKEN", "") else "not set",
    }
    critical_ok = all("online" in services[s] for s in ["qdrant", "database"])
    any_error   = any("offline" in v for v in services.values())
    overall = "operational" if (critical_ok and not any_error) else ("degraded" if critical_ok else "critical")
    log.info(f"OS/status: {overall}")
    return {"os": "fwg_ai_os", "version": "1.0.0",
            "status": overall, "services": services,
            "timestamp": datetime.utcnow().isoformat()}


@router.post("/reset", response_model=OSResponse)
async def soft_reset():
    """Soft reset: flush Redis cache + reload service singletons."""
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
