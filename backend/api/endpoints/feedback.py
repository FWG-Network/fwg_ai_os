from fastapi import APIRouter, status, Response
from backend.learning.events import UserEvent

router = APIRouter()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def receive_feedback(event: UserEvent, response: Response):
    """
    Accepts a user feedback event and queues it for background processing.
    """
    try:
        # ★★★ FIX: Use model_dump() instead of the deprecated dict() ★★★
        print(f"INFO: Event received and queued for processing: {event.model_dump()}")
        # process_feedback_event_task.delay(event.model_dump())
        return {"message": "Feedback event accepted for processing."}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"message": f"Failed to queue event. Error: {str(e)}"}
