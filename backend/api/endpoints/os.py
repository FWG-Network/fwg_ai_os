from fastapi import APIRouter

router = APIRouter()

@router.post("/run")
async def run_goal():
    return {"message": "AI-OS endpoint is active"}
