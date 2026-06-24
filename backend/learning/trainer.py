from .reward import RewardEngine
from .online_learning import OnlineLearning
from .events import UserEvent

# In a real system, we'd have a User Profile Store (e.g., Redis)
# For now, we use a simple in-memory dictionary to simulate it.
USER_PROFILE_DB = {} 

class Trainer:
    def __init__(self):
        self.reward_engine = RewardEngine()
        self.learning_engine = OnlineLearning()

    def train(self, event: UserEvent):
        """The main training loop for a single user event."""
        print(f"Training on event: {event.event_type} for user {event.user_id}")

        # 1. Load user profile (or create if new)
        profile = USER_PROFILE_DB.get(event.user_id, {"user_id": event.user_id})

        # 2. Calculate reward
        reward = self.reward_engine.calculate(event.event_type, event.value)
        
        # 3. Update interests via online learning
        updated_profile = self.learning_engine.update_interest(
            profile, 
            event.tags, 
            reward
        )

        # 4. Save the updated profile
        USER_PROFILE_DB[event.user_id] = updated_profile
        print(f"User {event.user_id} profile updated. New interests: {updated_profile.get('interests')}")
