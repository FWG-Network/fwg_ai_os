from fastapi import APIRouter, status, Response
from backend.learning.events import UserEvent
# from backend.learning.tasks import process_feedback_event_task # We will mock this for now

router = APIRouter()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def receive_feedback(event: UserEvent, response: Response):
    """
    Accepts a user feedback event and queues it for background processing.
    """
    try:
        # In production, this sends the task to the Celery queue.
        # process_feedback_event_task.delay(event.dict())
        print(f"INFO: Event received and queued for processing: {event.dict()}")
        return {"message": "Feedback event accepted for processing."}
    except Exception as e:
        # If the queue is down, we can't accept it.
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"message": f"Failed to queue event. Please try again later. Error: {str(e)}"}
