from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def process_multimodal_input():
    return {"message": "Multimodal endpoint is active"}
