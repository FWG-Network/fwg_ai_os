"""
backend/aios/tasks.py
Celery tasks for AIOS — wraps async orchestrator in sync context.
"""
import asyncio
from backend.core.logger import log

try:
    from backend.worker import celery_app
except Exception as e:
    log.warning(f"[AIOSTasks] Celery unavailable: {e}")
    celery_app = None


def _run_async(coro):
    """Run async coroutine in Celery sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Already in async context — create new loop
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def execute_agent_task(task_description: str, user_id: str = "system") -> str:
    """
    AIOS Celery task — runs LLM Orchestrator async in sync context.
    ✅ Fix: asyncio.run() wrapper for async generate_response()
    """
    log.info(f"[AIOSTasks] task='{task_description[:60]}' user={user_id}")
    try:
        from backend.lim.orchestrator import llm_orchestrator

        # ✅ Fix: wrap async in sync
        response_data = _run_async(
            llm_orchestrator.generate_response(
                query=task_description,
                user_id=user_id,
            )
        )
        result = response_data.get("response", "No response generated.")
        log.info(f"[AIOSTasks] ✅ Done ({len(result)} chars)")
        return result

    except Exception as e:
        log.error(f"[AIOSTasks] Failed: {e}")
        return f"Task failed: {e}"


# Register with Celery if available
if celery_app:
    execute_agent_task = celery_app.task(
        name="aios.execute_agent_task"
    )(execute_agent_task)
