import asyncio
import httpx
from fastapi import HTTPException

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import FeedbackEvent, TaskRequest, TaskStatusResponse


class WorkerClient:
    """
    HTTP client for the Celery worker service.
    ✅ Retry logic (agent_client)
    ✅ Typed schemas (dev)
    ✅ Generic helpers (mine)
    """

    MAX_RETRIES = 3
    RETRY_DELAYS = [0.5, 1.0]  # fast retry — local docker service, មិនមែន remote HF Space #add new

    def __init__(self):
        self.base_url = f"http://{settings.WORKER_HOST}:{settings.WORKER_PORT}"
        log.info(f"[WorkerClient] initialized → {self.base_url}")

    # ─── Feedback ─────────────────────────────────────────────────────
    async def submit_feedback(self, event: FeedbackEvent) -> dict:
        """Queue feedback event to worker."""
        return await self._post(
            "/feedback",
            event.model_dump(),
            timeout=5.0,
        )

    # ─── Task ─────────────────────────────────────────────────────────
    async def submit_task(self, task: TaskRequest) -> dict:
        """Queue autonomous task to worker."""
        return await self._post(
            "/task/submit",
            task.model_dump(),
            timeout=60.0,
        )

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Check status of a queued task."""
        data = await self._get(f"/task/status/{task_id}", timeout=5.0)
        return TaskStatusResponse(**data)

    # ─── Health ───────────────────────────────────────────────────────
    async def health(self) -> dict:
        return await self._get("/health", timeout=10.0)

    # ─── Generic Helpers + ✅ Retry (agent_client pattern) ─────────────
    async def _post(self, path: str, payload: dict, timeout: float = 10.0) -> dict:
        return await self._request("POST", path, json=payload, timeout=timeout)

    async def _get(self, path: str, timeout: float = 10.0) -> dict:
        return await self._request("GET", path, timeout=timeout)

    async def _request(
        self, method: str, path: str,
        timeout: float = 10.0, **kwargs
    ) -> dict:
        url      = f"{self.base_url}{path}"
        last_exc = None

        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.request(method, url, **kwargs)
                    resp.raise_for_status()
                    return resp.json()

            # ✅ agent_client: retry on connection issues
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_exc = e
                if attempt < self.MAX_RETRIES - 1:
                    wait = self.RETRY_DELAYS[min(attempt, len(self.RETRY_DELAYS) - 1)] #add new
                    log.warning(
                        f"[WorkerClient] {method} {url} failed "
                        f"(attempt {attempt+1}/{self.MAX_RETRIES}) "
                        f"— retry in {wait}s"
                    )
                    await asyncio.sleep(wait)

            # ✅ Dev: re-raise HTTP errors immediately
            except httpx.HTTPStatusError as e:
                log.error(f"[WorkerClient] HTTP {e.response.status_code} → {url}")
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Worker error: {e.response.text}",
                )

        log.error(f"[WorkerClient] {method} {url} failed after {self.MAX_RETRIES} retries")
        raise HTTPException(
            status_code=503,
            detail=f"Worker unavailable after {self.MAX_RETRIES} retries: {last_exc}",
        )


worker_client = WorkerClient()
