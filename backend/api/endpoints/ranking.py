from fastapi import APIRouter

router = APIRouter()

@router.post("/")
async def rank_content():
    return {"message": "Ranking endpoint is active"}
