from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def receive_feedback():
    return {"message": "Feedback endpoint is active"}
