from backend.learning.events import EventType

class RewardEngine:
    """
    A stateless service class responsible for calculating rewards based on user events.
    All methods are class methods as they do not depend on instance state.
    
    ★★★ This file ONLY defines the class, it does NOT create an instance. ★★★
    """
    
    REWARDS = {
        EventType.VIEW: 1,
        EventType.CLICK: 2,
        EventType.WATCH: 4,
        EventType.LIKE: 6,
        EventType.SAVE: 8,
        EventType.SHARE: 10,
        EventType.FOLLOW: 12,
        EventType.SKIP: -6,
    }

    @classmethod
    def calculate(cls, event_type: EventType, value: float = 0.0) -> int:
        """
        Calculates a reward score for a given event type and value.
        """
        base_reward = cls.REWARDS.get(event_type, 0)

        if event_type == EventType.WATCH and value > 0:
            if value > 0.9: return 8
            if value > 0.5: return 4
            return -6

        return base_reward

# NO INSTANCE CREATION HERE. This is critical for preventing circular imports.
