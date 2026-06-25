from backend.worker import celery_app
from backend.core.services import reward_service, online_learning_service, redis_client
from .trainer import Trainer
from .events import UserEvent
import json

# Create the trainer instance here, injecting the real services
# This instance is created once per worker process.
production_trainer = Trainer(
    reward_engine=reward_service,
    learning_engine=online_learning_service
)

@celery_app.task(name="process_feedback_event")
def process_feedback_event_task(event_data: dict):
    """
    The Celery task that connects everything for production.
    """
    event = UserEvent(**event_data)
    profile_key = f"profile:{event.user_id}"

    # 1. Load from Redis
    profile_json = redis_client.get(profile_key)
    profile = json.loads(profile_json) if profile_json else {"user_id": event.user_id}

    # 2. Use the trainer to get the updated profile
    updated_profile = production_trainer.process_and_update_profile(profile, event)

    # 3. Save back to Redis
    redis_client.set(profile_key, json.dumps(updated_profile))
    print(f"User {event.user_id} profile updated in Redis via worker.")
