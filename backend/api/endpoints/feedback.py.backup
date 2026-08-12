from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from backend.models.schemas import FeedbackEvent
from backend.models.db import get_db
from backend.core.logger import log

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# ─── Validation constants ─────────────────────────────────────────────
VALID_EVENT_TYPES = {"like", "dislike", "skip", "watch_time", "impression"}


# ─── POST /feedback/ ──────────────────────────────────────────────────
@router.post("/")
async def submit_user_feedback(
    event: FeedbackEvent,
    db: Session = Depends(get_db),
):
    """
    Submit user feedback event.
    Queues to Celery worker when available, fallback to direct processing.
    """
    log.info(
        f"[Feedback] user={event.user_id} "
        f"item={event.item_id} "
        f"type={event.event_type} "
        f"value={event.value}"
    )

    # ── Validate event_type ──────────────────────────────────────────
    if event.event_type not in VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid event_type '{event.event_type}'. "
                   f"Must be one of: {VALID_EVENT_TYPES}"
        )

    # ── Validate value range ─────────────────────────────────────────
    if not (-1.0 <= event.value <= 1.0):
        raise HTTPException(
            status_code=422,
            detail=f"Value must be between -1.0 and 1.0, got {event.value}"
        )

    # ── ✅ Dev: Try Celery worker first ───────────────────────────────
    try:
        from backend.services.worker_client import worker_client
        response = await worker_client.submit_feedback(event)
        log.info(f"[Feedback] ✅ Queued to worker task_id={response.get('task_id')}")
        return {
            "status":     "queued",
            "task_id":    response.get("task_id", "N/A"),
            "user_id":    event.user_id,
            "item_id":    event.item_id,
            "event_type": event.event_type,
        }
    except Exception as e:
        log.warning(f"[Feedback] Worker unavailable, fallback to direct: {e}")

    # ── ✅ Mine: Fallback — direct processing ─────────────────────────
    try:
        from backend.learning.events import learning_event_service
        await learning_event_service.record(event)
        log.info("[Feedback] ✅ Recorded to learning system")
    except Exception as e:
        log.warning(f"[Feedback] Learning skipped: {e}")

    try:
        from backend.services.personalization_engine import personalization_engine_service
        personalization_engine_service.update(
            event.user_id,
            event.item_id,
            event.event_type,
            event.value,
        )
        log.info("[Feedback] ✅ Personalization updated")
    except Exception as e:
        log.warning(f"[Feedback] Personalization skipped: {e}")

    return {
        "status":     "received",
        "user_id":    event.user_id,
        "item_id":    event.item_id,
        "event_type": event.event_type,
        "value":      event.value,
    }


# ─── GET /feedback/health ─────────────────────────────────────────────
@router.get("/health")
async def feedback_health():
    return {"status": "ok", "endpoint": "feedback"}
