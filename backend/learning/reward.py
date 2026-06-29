"""
backend/learning/reward.py
Reward Engine — calculate reward scores from user events.
No instance created here (prevents circular imports).
"""
from backend.core.logger import log

try:
    from backend.learning.events import EventType
except ImportError:
    # ✅ Fallback if events.py not ready
    from enum import Enum
    class EventType(str, Enum):
        VIEW       = "view"
        CLICK      = "click"
        WATCH      = "watch_time"
        LIKE       = "like"
        SAVE       = "save"
        SHARE      = "share"
        FOLLOW     = "follow"
        SKIP       = "skip"
        DISLIKE    = "dislike"
        IMPRESSION = "impression"


class RewardEngine:
    """
    Stateless reward calculator.
    No instance state → all class methods.
    """

    REWARDS = {
        EventType.VIEW:       1,
        EventType.CLICK:      2,
        EventType.WATCH:      4,
        EventType.LIKE:       6,
        EventType.SAVE:       8,
        EventType.SHARE:      10,
        EventType.FOLLOW:     12,
        EventType.SKIP:       -6,
        EventType.DISLIKE:    -8,
        EventType.IMPRESSION: 0,
    }

    @classmethod
    def calculate(cls, event_type: EventType, value: float = 0.0) -> int:
        """
        Calculate reward for event.
        WATCH reward scales with completion rate (value = 0.0 → 1.0).
        """
        if event_type == EventType.WATCH and value > 0:
            if value > 0.9:   return 8    # 90%+ watched = excellent
            if value > 0.5:   return 4    # 50-90% = good
            if value > 0.1:   return 1    # 10-50% = neutral
            return -2                      # <10% = poor

        base = cls.REWARDS.get(event_type, 0)
        log.debug(f"[RewardEngine] event={event_type} value={value} → reward={base}")
        return base

    @classmethod
    def calculate_from_str(cls, event_type_str: str, value: float = 0.0) -> int:
        """
        Calculate reward from string event type.
        Used by FeedbackEvent (schema uses str, not Enum).
        """
        mapping = {
            "like":        EventType.LIKE,
            "dislike":     EventType.DISLIKE,
            "skip":        EventType.SKIP,
            "watch_time":  EventType.WATCH,
            "impression":  EventType.IMPRESSION,
            "view":        EventType.VIEW,
            "click":       EventType.CLICK,
            "save":        EventType.SAVE,
            "share":       EventType.SHARE,
            "follow":      EventType.FOLLOW,
        }
        event = mapping.get(event_type_str.lower())
        if event is None:
            log.warning(f"[RewardEngine] Unknown event_type: '{event_type_str}' → 0")
            return 0
        return cls.calculate(event, value)


# ⚠️ NO instance creation here — prevents circular imports
# Use RewardEngine.calculate() directly as class method
# Or create instance in services.py: reward_service = RewardEngine()
