"""
backend/aios/executor.py
Executor — Tool Router for AIOS tasks.
Routes each task.tool_name → correct service.
"""
import asyncio
import json
from typing import Any, List, Optional

from sqlalchemy.orm import Session
from backend.models.db import Task as TaskModel
from backend.core.logger import log

# ── Supported tools (aligned with task_planner.py) ───────────────────
SUPPORTED_TOOLS = {
    "trend_scanner",
    "trend_analyzer",
    "llm_agent",
    "web_search",
    "vector_memory",
    "ranking_engine",
}


class Executor:
    """
    Tool Router — inspects task.tool_name + task.tool_params
    and routes to correct service.

    ✅ Fix: async throughout
    ✅ Fix: tool_params used
    ✅ Fix: consistent signature (user_id, not goal_owner_id)
    ✅ Fix: no missing service imports
    """

    # ── GROUP execution (parallel within stage) ───────────────────────
    async def execute_task_group(
        self,
        tasks:   List[TaskModel],
        db:      Session,
        user_id: str = "aios_system",
        execution_context: dict = None,
    ) -> None:
        """Run all eligible tasks in a stage concurrently."""
        if not tasks:
            return

        execution_context = execution_context or {}

        coroutines = [
            self.execute_task(
                task,
                db,
                user_id,
                execution_context.get(task.id),
            )
            for task in tasks
            if task.status == "pending"
        ]
        executable_tasks = [task for task in tasks if task.status == "pending"]
        results = await asyncio.gather(
            *coroutines,
            return_exceptions=True,
        )

        for task, result in zip(executable_tasks, results):
            if isinstance(result, Exception):
                task.status = "failed"
                task.result = {"error": str(result)}
                log.error(f"[Executor] Task {task.id} failed: {result}")
            else:
                task.status = "completed"
                # ✅ store as JSON dict
                task.result = result if isinstance(result, dict) else {"output": str(result)}
                log.info(f"[Executor] Task {task.id} ✅ tool={task.tool_name}")

    # ── SINGLE task execution ─────────────────────────────────────────
    async def execute_task(
        self,
        task:    TaskModel,
        db:      Session,
        user_id: str = "aios_system",
        resolved_inputs: dict = None,
    ) -> Any:
        """
        Route task to correct tool.
        Uses task.tool_name + task.tool_params.

        resolved_inputs: optional dict of {input_name: value} from dependency resolution.
        """
        tool   = task.tool_name or "llm_agent"
        # ✅ Fix: use tool_params from task_planner
        params = task.tool_params or {}
        resolved_inputs = resolved_inputs or {}

        if task.status != "pending":
            raise RuntimeError(
                f"Task {task.id} is not eligible for execution: status={task.status}"
            )

        log.info(
            f"[Executor] Task {task.id} "
            f"tool={tool} params={params}"
        )

        task.status = "running"

        try:
            # ── trend_scanner ─────────────────────────────────────────
            if tool == "trend_scanner":
                from backend.services.connectors.youtube import youtube_connector
                keyword = params.get("theme_keyword", "viral trend")
                result  = await youtube_connector.suggest_from_known_channels(
                    db=db,
                    theme_keyword=keyword,
                )
                return {
                    "tool":     "trend_scanner",
                    "keyword":  keyword,
                    "creators": result.get("source_creators_ranked", []),
                    "videos":   result.get("matched_videos", []),
                }

            # ── trend_analyzer ────────────────────────────────────────
            elif tool == "trend_analyzer":
                from backend.services.discovery_engine import discovery_engine_service
                from backend.services.ranking_engine import ranking_engine_service

                # ✅ NEW: Support propagated input from Stage 1
                if "candidates" in resolved_inputs:
                    candidates = resolved_inputs["candidates"]
                    log.info(f"[Executor] Task {task.id} using propagated candidates from Stage 1")
                else:
                    keyword    = params.get("theme_keyword", task.description)
                    candidates = await discovery_engine_service.discover(keyword)

                ranked = ranking_engine_service.rank(candidates, user_id=user_id)
                return {
                    "tool":    "trend_analyzer",
                    "total":   len(ranked),
                    "results": ranked[:10],
                }

            # ── web_search ────────────────────────────────────────────
            elif tool == "web_search":
                from backend.services.discovery_engine import discovery_engine_service
                query      = params.get("query", task.description)
                candidates = await discovery_engine_service.discover(query)
                return {
                    "tool":    "web_search",
                    "query":   query,
                    "results": candidates[:10],
                }

            # ── vector_memory ─────────────────────────────────────────
            elif tool == "vector_memory":
                from backend.lim.vector_memory import vector_memory_service
                query   = params.get("query", task.description)
                top_k   = params.get("top_k", 5)
                results = vector_memory_service.search(query, top_k=top_k)
                return {
                    "tool":    "vector_memory",
                    "query":   query,
                    "results": results,
                }

            # ── ranking_engine ────────────────────────────────────────
            elif tool == "ranking_engine":
                from backend.services.ranking_engine import ranking_engine_service
                candidates = params.get("candidates", [])
                ranked     = ranking_engine_service.rank(candidates, user_id=user_id)
                return {
                    "tool":   "ranking_engine",
                    "ranked": ranked,
                }

            # ── llm_agent (default) ───────────────────────────────────
            elif tool == "llm_agent":
                from backend.lim.orchestrator import llm_orchestrator
                # ✅ Fix: await async generate_response
                result = await llm_orchestrator.generate_response(
                    query=task.description,
                    user_id=user_id,
                    task_type=params.get("task_type", "default"),
                )
                return {
                    "tool":      "llm_agent",
                    "response":  result.get("response", ""),
                    "model":     result.get("model_used", ""),
                }

            else:
                raise ValueError(
                    f"Unknown tool '{tool}'. "
                    f"Supported: {SUPPORTED_TOOLS}"
                )

        except Exception as e:
            log.error(f"[Executor] Tool '{tool}' failed: {e}")
            raise


# ── Global instance ───────────────────────────────────────────────────
executor_service = Executor()
