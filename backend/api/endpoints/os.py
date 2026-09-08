"""
backend/api/endpoints/os.py
Autonomous OS endpoint — Fixed v4
"""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import TaskRequest, TaskStatusResponse
from backend.models.db import (
    AIOSIdempotencyRecord,
    Goal as GoalModel,
    get_db,
)
from backend.services.intelligence_engine import intelligence_engine_service
from backend.services.evaluation_engine import evaluation_engine_service

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
    idempotency_key: Optional[str]       = None


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
    idempotency_record_id: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def _request_fingerprint(scope: str, user_id: str, payload: Dict[str, Any]) -> str:
    canonical = json.dumps(
        {"scope": scope, "user_id": user_id, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _require_idempotency_key(key: Optional[str]) -> str:
    if not key or not key.strip():
        raise HTTPException(status_code=422, detail="idempotency_key is required")
    return key.strip()


def _reserve_idempotency(
    db: Session,
    *,
    scope: str,
    user_id: str,
    key: str,
    fingerprint: str,
) -> tuple[AIOSIdempotencyRecord, bool]:
    existing = (
        db.query(AIOSIdempotencyRecord)
        .filter_by(scope=scope, user_id=user_id, idempotency_key=key)
        .one_or_none()
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key was already used with a different request",
            )
        return existing, False

    record = AIOSIdempotencyRecord(
        scope=scope,
        user_id=user_id,
        idempotency_key=key,
        request_fingerprint=fingerprint,
        status="reserved",
    )
    db.add(record)
    try:
        db.commit()
        db.refresh(record)
        return record, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(AIOSIdempotencyRecord)
            .filter_by(scope=scope, user_id=user_id, idempotency_key=key)
            .one()
        )
        if existing.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=409,
                detail="idempotency_key was already used with a different request",
            )
        return existing, False


def _replay_idempotency(
    record: AIOSIdempotencyRecord,
    db: Session,
    *,
    response_type: str,
    plan: Optional[List[str]] = None,
    agent: Optional[str] = None,
):
    if record.goal_id is not None:
        goal = db.get(GoalModel, record.goal_id)
        if goal is not None:
            status = goal.status
        else:
            status = record.status
    else:
        status = record.status

    task_id = str(record.goal_id) if record.goal_id is not None else None

    if task_id is None:
        payload_status = "reserved"
        record_id = str(record.id)
    else:
        payload_status = status
        record_id = None

    if response_type == "task":
        payload = TaskStatusResponse(
            task_id=task_id,
            status=payload_status,
            idempotency_record_id=record_id,
        )
        if task_id is None:
            return JSONResponse(
                status_code=202,
                content=payload.model_dump(exclude_none=True),
            )
        return payload

    payload = OSResponse(
        status=payload_status,
        task_id=task_id,
        plan=plan,
        agent=agent,
        idempotency_record_id=record_id,
    )
    if task_id is None:
        return JSONResponse(
            status_code=202,
            content=payload.model_dump(exclude_none=True),
        )
    return payload


def _complete_idempotency(
    db: Session,
    record: AIOSIdempotencyRecord,
    *,
    status: str,
    goal_id: Optional[int] = None,
    worker_task_id: Optional[str] = None,
) -> None:
    record.status = status
    record.goal_id = goal_id
    record.worker_task_id = worker_task_id
    if status in {"completed", "completed_partial", "failed"}:
        record.completed_at = datetime.now(timezone.utc)
    db.commit()


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
async def submit_autonomous_os_goal(
    request: TaskRequest,
    db: Session = Depends(get_db),
):
    """Submit high-level goal to Autonomous OS."""
    user_id = request.user_id or "system"
    idempotency_key = _require_idempotency_key(request.idempotency_key)
    scope = "os.submit_goal"
    record, is_new = _reserve_idempotency(
        db,
        scope=scope,
        user_id=user_id,
        key=idempotency_key,
        fingerprint=_request_fingerprint(
            scope,
            user_id,
            {"goal": request.goal},
        ),
    )
    if not is_new:
        return _replay_idempotency(record, db, response_type="task")

    log.info(f"[OS] Goal: '{request.goal}' user={user_id}")

    try:
        # Local AIOS is the authoritative execution path.
        from backend.aios.autonomous_loop import autonomous_loop_service

        goal = await autonomous_loop_service.run(
            goal_description=request.goal,
            user_id=user_id,
            db=db,
        )
        _complete_idempotency(
            db,
            record,
            status=goal.status,
            goal_id=goal.id,
        )

        return TaskStatusResponse(
            task_id=str(goal.id),
            status=goal.status,
        )

    except Exception as e:
        log.error(f"[OS] submit_goal local AIOS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/task/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    """Get status from the authoritative local AIOS Goal state."""
    try:
        goal_id = int(task_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=404,
            detail=f"Local task not found: {task_id}",
        )

    goal = db.get(GoalModel, goal_id)
    if goal is None:
        raise HTTPException(
            status_code=404,
            detail=f"Local task not found: {task_id}",
        )

    failed_tasks = [
        task
        for task in goal.tasks
        if task.status == "failed"
    ]

    error = None
    result = None

    if failed_tasks:
        latest_failed = failed_tasks[-1]
        error_payload = latest_failed.result or {}
        if isinstance(error_payload, dict):
            error = error_payload.get("error")
        if error is None:
            error = f"Task {latest_failed.id} failed"
        result = latest_failed.result

    return TaskStatusResponse(
        task_id=str(goal.id),
        status=goal.status,
        result=result,
        error=error,
    )


@router.post("/execute", response_model=OSResponse)
async def execute_command(
    cmd: OSCommand,
    db: Session = Depends(get_db),
):
    """Natural language → create_plan → execute."""
    log.info(f"[OS] execute: '{cmd.command}' user={cmd.user_id}")
    planner = _get_planner()
    record: Optional[AIOSIdempotencyRecord] = None
    try:
        if cmd.async_mode:
            user_id = cmd.user_id or "system"
            idempotency_key = _require_idempotency_key(cmd.idempotency_key)
            scope = "os.execute.async"
            record, is_new = _reserve_idempotency(
                db,
                scope=scope,
                user_id=user_id,
                key=idempotency_key,
                fingerprint=_request_fingerprint(
                    scope,
                    user_id,
                    {"command": cmd.command},
                ),
            )
            if not is_new:
                return _replay_idempotency(record, db, response_type="os")

        staged_plan = await asyncio.to_thread(
            planner.create_plan,
            cmd.command,
            cmd.user_id,
        )
        task_models = _flatten_tasks(staged_plan)

        steps         = [t.description for t in task_models]
        primary_agent = task_models[0].tool_name if task_models else "unknown"

        if cmd.async_mode:
            assert record is not None
            try:
                # Local AIOS is the authoritative execution path.
                from backend.aios.autonomous_loop import (
                    autonomous_loop_service,
                )

                goal = await autonomous_loop_service.run(
                    goal_description=cmd.command,
                    user_id=cmd.user_id or "system",
                    db=db,
                )
                _complete_idempotency(
                    db,
                    record,
                    status=goal.status,
                    goal_id=goal.id,
                )

                return OSResponse(
                    status=goal.status,
                    task_id=str(goal.id),
                    plan=steps,
                    agent=primary_agent,
                )

            except Exception as e:
                log.error(f"[OS] execute local AIOS failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

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

            enriched = intelligence_engine_service.analyze(
                candidates,
                editorial_intent={
                    "topic": topic,
                },
            )
            evaluated = evaluation_engine_service.evaluate(
                enriched,
            )

            # ✅ rank() is sync
            ranked = _get_ranking().rank(
                evaluated,
                user_id=req.user_id,
            )
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
    any_degraded = any(
        value == "degraded" or "offline" in value
        for value in services.values()
    )
    overall = (
        "operational"
        if critical_ok and not any_degraded
        else ("degraded" if critical_ok else "critical")
    )

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
