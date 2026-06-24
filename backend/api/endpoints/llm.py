from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
async def generate_response():
    return {"message": "LLM endpoint is active"}
