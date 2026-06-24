import json
from .events import UserEvent
from .reward import reward_service  # Using the service instance pattern
from .online_learning import online_learning_service # Using the service instance pattern

# ★★★ FIX: Removed the in-memory USER_PROFILE_DB dictionary ★★★
# Instead, we import the centralized, shared Redis client.
from backend.core.services import redis_client

class Trainer:
    """
    The Trainer class is responsible for the online learning loop.
    It processes user events, calculates rewards, and updates user profiles
    in a persistent, shared state manager (Redis).
    """

    def train(self, event: UserEvent):
        """
        The main training loop for a single user event.
        This process is now stateless and production-ready.
        """
        print(f"Training on event: {event.event_type} for user {event.user_id}")
        
        profile_key = f"profile:{event.user_id}"

        # 1. ★★★ FIX: Load user profile from the shared Redis store ★★★
        try:
            profile_json = redis_client.get(profile_key)
            # If a profile exists, load it; otherwise, create a new one.
            if profile_json:
                profile = json.loads(profile_json)
            else:
                profile = {"user_id": event.user_id, "interests": {}}
        except Exception as e:
            print(f"ERROR: Could not load profile for user {event.user_id} from Redis. Error: {e}")
            # In a real system, you might want to stop or handle this more gracefully.
            return

        # 2. Calculate reward using the reward service
        reward = reward_service.calculate(event.event_type, event.value)
        
        # 3. Update interests via the online learning service
        updated_profile = online_learning_service.update_interest(
            profile, 
            event.tags, 
            reward
        )

        # 4. ★★★ FIX: Save the updated profile back to the shared Redis store ★★★
        try:
            redis_client.set(profile_key, json.dumps(updated_profile))
            print(f"User {event.user_id} profile updated in Redis. New interests: {updated_profile.get('interests')}")
        except Exception as e:
            print(f"ERROR: Could not save profile for user {event.user_id} to Redis. Error: {e}")


# Create a single, reusable instance of the Trainer service
trainer_service = Trainer()
