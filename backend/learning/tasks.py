"""
backend/learning/tasks.py
Celery tasks — async feedback processing via worker.
"""
import json
from backend.core.logger import log


# ── Celery app ────────────────────────────────────────────────────────
try:
    from backend.worker import celery_app
except Exception as e:
    log.warning(f"[Tasks] Celery unavailable: {e}")
    celery_app = None


# ── Celery Task ───────────────────────────────────────────────────────
def process_feedback_event_task(event_data: dict):
    """
    Celery task — process feedback event:
    1. Parse UserEvent
    2. Calculate reward
    3. Update Redis via PersonalizationEngine (consistent key format)
    4. Update in-memory profile via Trainer (legacy compatibility)
    """
    log.info(f"[Tasks] Processing feedback: {event_data.get('event_type')} user={event_data.get('user_id')}")

    try:
        from backend.learning.events import UserEvent
        event = UserEvent(**event_data)
    except Exception as e:
        log.error(f"[Tasks] Invalid event data: {e}")
        return {"status": "error", "error": str(e)}

    # ── Step 1: Calculate reward ──────────────────────────────────────
    try:
        from backend.learning.reward import RewardEngine
        reward = RewardEngine.calculate(event.event_type, event.value)
        log.info(f"[Tasks] reward={reward:+d} for {event.event_type}")
    except Exception as e:
        log.warning(f"[Tasks] Reward calc failed: {e}")
        reward = 0

    # ── Step 2: Update PersonalizationEngine (Redis) ──────────────────
    # ✅ Fix: use PersonalizationEngine — correct key format + signal extraction
    try:
        from backend.services.personalization_engine import personalization_engine_service

        item_meta = {
            "platform": event.platform,
            "tags":     event.tags,
            "channel":  event.channel,
            "category": event.category,
        }
        personalization_engine_service.update(
            user_id=event.user_id,
            item_id=event.item_id,
            event_type=event.event_type.value,
            value=event.value,
            item_meta=item_meta,
        )
        log.info(f"[Tasks] ✅ PersonalizationEngine updated user={event.user_id}")

    except Exception as e:
        log.error(f"[Tasks] PersonalizationEngine update failed: {e}")

    # ── Step 3: Trainer profile update (legacy + ML) ──────────────────
    try:
        from backend.core.services import redis_client
        from backend.learning.trainer import Trainer
        from backend.learning.reward import RewardEngine
        from backend.learning.online_learning import OnlineLearning

        if redis_client:
            profile_key  = f"user:{event.user_id}:profile"  # ✅ consistent key
            profile_json = redis_client.get(profile_key)
            profile      = json.loads(profile_json) if profile_json else {"user_id": event.user_id}

            trainer = Trainer(
                reward_engine=RewardEngine(),
                learning_engine=OnlineLearning(),
            )
            updated = trainer.process_and_update_profile(profile, event)
            redis_client.set(profile_key, json.dumps(updated))
            log.info(f"[Tasks] ✅ Trainer profile updated user={event.user_id}")

    except Exception as e:
        log.warning(f"[Tasks] Trainer update skipped: {e}")

    return {
        "status":     "processed",
        "user_id":    event.user_id,
        "event_type": event.event_type.value,
        "reward":     reward,
    }


# ── Register Celery task if available ────────────────────────────────
if celery_app:
    process_feedback_event_task = celery_app.task(
        name="process_feedback_event"
    )(process_feedback_event_task)
