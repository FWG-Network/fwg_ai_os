from fastapi import APIRouter, status, Response
from backend.learning.events import UserEvent

router = APIRouter()

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def receive_feedback(event: UserEvent, response: Response):
    try:
        print(f"INFO: Event received: {event.model_dump()}")
        return {"message": "Feedback event accepted for processing."}
    except Exception as e:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"message": f"Failed to queue event. Error: {str(e)}"}
