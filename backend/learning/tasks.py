from backend.worker import celery_app
from .events import UserEvent
from .trainer import Trainer

# Initialize a single trainer instance for this worker process
trainer = Trainer()

@celery_app.task(name="process_feedback_event")
def process_feedback_event_task(event_data: dict):
    """
    Asynchronous task to process a user feedback event.
    """
    event = UserEvent(**event_data)
    trainer.train(event)
    return {"status": "success", "processed_event": event.event_type}
