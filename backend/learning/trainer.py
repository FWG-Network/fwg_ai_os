import json
from .events import UserEvent
# ★★★ FIX: Import the *classes*, not the service instances ★★★
from .reward import RewardEngine
from .online_learning import OnlineLearning
# We no longer need redis_client here, the caller will handle persistence.

class Trainer:
    # ★★★ FIX: Use Dependency Injection ★★★
    def __init__(self, reward_engine: RewardEngine, learning_engine: OnlineLearning):
        """
        Initializes the Trainer with its dependencies. This makes the class
        decoupled and easier to test.
        """
        self.reward_engine = reward_engine
        self.learning_engine = learning_engine

    def process_and_update_profile(self, profile: dict, event: UserEvent) -> dict:
        """
        Processes an event and returns the updated profile without saving it.
        This makes the core logic stateless and reusable.
        """
        reward = self.reward_engine.calculate(event.event_type, event.value)
        updated_profile = self.learning_engine.update_interest(
            profile,
            event.tags,
            reward
        )
        return updated_profile
