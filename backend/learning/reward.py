# Import the Enum directly to avoid potential circular import issues with other event files.
from backend.learning.events import EventType

class RewardEngine:
    """
    A stateless service class responsible for calculating rewards based on user events.
    All methods are class methods as they do not depend on instance state.
    """
    
    # ★★★ FIX: All reward definitions are now correctly inside the dictionary ★★★
    REWARDS = {
        EventType.VIEW: 1,
        EventType.CLICK: 2,
        EventType.WATCH: 4,  # Base reward, will be adjusted by watch ratio
        EventType.LIKE: 6,
        EventType.SAVE: 8,
        EventType.SHARE: 10,
        EventType.FOLLOW: 12,
        EventType.SKIP: -6,
    }

    # ★★★ FIX: Using a single, correct @classmethod implementation ★★★
    @classmethod
    def calculate(cls, event_type: EventType, value: float = 0.0) -> int:
        """
        Calculates a reward score for a given event type and value.

        Args:
            event_type: The type of the user event.
            value: An optional value, primarily for watch time ratio.

        Returns:
            An integer representing the calculated reward.
        """
        # Get the base reward from the dictionary, default to 0 if not found.
        base_reward = cls.REWARDS.get(event_type, 0)

        # Special logic for 'watch' events to override the base reward.
        if event_type == EventType.WATCH and value > 0:
            if value > 0.9: return 8    # High reward for long watch time
            if value > 0.5: return 4    # Medium reward
            return -6                   # Penalize very short watch times (treat like a skip)

        return base_reward

# ★★★ NOTE: The service instance is now created in backend/core/services.py ★★★
# We do NOT create reward_service = RewardEngine() here anymore.
