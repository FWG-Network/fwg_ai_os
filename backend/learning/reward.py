from .events import EventType

class RewardEngine:
    REWARDS = {
        EventType.VIEW: 1,
        EventType.CLICK: 2,
        EventType.WATCH: 4, # Base reward, can be multiplied by watch ratio
        EventType.LIKE: 6,
        EventType.SAVE: 8,
        EventType.SHARE: 10,
        EventType.FOLLOW: 12,
        EventType.SKIP: -6,
    }

    @classmethod
    def calculate(cls, event_type: EventType, value: float = 0.0) -> int:
        base_reward = cls.REWARDS.get(event_type, 0)

        if event_type == EventType.WATCH and value > 0:
            # More reward for longer watch times
            if value > 0.9: return 8
            if value > 0.5: return 4
            return -2 # Penalize very short watch times

        return base_reward
