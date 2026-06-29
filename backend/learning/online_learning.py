"""
backend/learning/online_learning.py
Online Learning — update user interests from feedback events.
Integrates with PersonalizationEngine (Redis) for persistence.
"""
from typing import Optional
from backend.core.logger import log


class OnlineLearning:
    """
    Real-time interest learning from user feedback.

    ✅ Fix: persists to Redis via PersonalizationEngine
    ✅ Fix: uses RewardEngine for reward calculation
    ✅ Fix: integrates with FeedbackEvent schema
    """

    LEARNING_RATE = 0.1

    # ── UPDATE from FeedbackEvent ──────────────────────────────────────
    async def process_feedback(
        self,
        user_id:    str,
        item_id:    str,
        event_type: str,
        value:      float = 1.0,
        item_meta:  Optional[dict] = None,
    ) -> dict:
        """
        Process feedback → calculate reward → update Redis interests.
        Main entry point from /feedback endpoint.
        """
        log.info(
            f"[OnlineLearning] user={user_id} "
            f"event={event_type}({value:.2f}) item={item_id}"
        )

        # ── Calculate reward ──────────────────────────────────────────
        try:
            from backend.learning.reward import RewardEngine
            reward = RewardEngine.calculate_from_str(event_type, value)
        except Exception as e:
            log.warning(f"[OnlineLearning] Reward calc failed: {e} → reward=0")
            reward = 0

        # ── Persist to Redis via PersonalizationEngine ────────────────
        # ✅ Fix: not just in-memory dict — saved to Redis!
        try:
            from backend.services.personalization_engine import (
                personalization_engine_service,
            )
            personalization_engine_service.update(
                user_id=user_id,
                item_id=item_id,
                event_type=event_type,
                value=value,
                item_meta=item_meta or {},
            )
            log.info(f"[OnlineLearning] ✅ Interests updated reward={reward:+d}")
        except Exception as e:
            log.warning(f"[OnlineLearning] Personalization update failed: {e}")

        return {
            "user_id":    user_id,
            "item_id":    item_id,
            "event_type": event_type,
            "reward":     reward,
            "status":     "processed",
        }

    # ── UPDATE in-memory profile (legacy) ─────────────────────────────
    def update_interest(
        self,
        profile:    dict,
        tags:       list,
        reward:     int,
    ) -> dict:
        """
        Update in-memory profile dict.
        Legacy method — use process_feedback() for Redis persistence.
        """
        if "interests" not in profile:
            profile["interests"] = {}

        for tag in tags:
            current = profile["interests"].get(tag, 0.0)
            update  = reward * self.LEARNING_RATE
            profile["interests"][tag] = round(current + update, 4)
            log.debug(
                f"[OnlineLearning] tag={tag} "
                f"{current:.3f} → {profile['interests'][tag]:.3f}"
            )

        return profile


# ── Global instance ───────────────────────────────────────────────────
online_learning_service = OnlineLearning()
