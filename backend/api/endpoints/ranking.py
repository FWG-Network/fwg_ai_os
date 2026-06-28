from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from backend.services.ranking_engine import ranking_engine_service
from backend.core.logger import log

router = APIRouter(prefix="/ranking", tags=["Ranking"])


class RankRequest(BaseModel):
    candidates: List[dict]
    user_id:    Optional[str] = None


@router.post("/rank")
async def rank_content(request: RankRequest):
    """Rank a list of content candidates."""
    log.info(f"[Ranking] {len(request.candidates)} items user='{request.user_id}'")

    if not request.candidates:
        raise HTTPException(status_code=422, detail="candidates list is empty")

    # ✅ rank() is sync — NO await
    ranked = ranking_engine_service.rank(
        request.candidates,
        user_id=request.user_id,
    )

    return {
        "total":   len(ranked),
        "ranked":  ranked,
    }


@router.get("/health")
async def ranking_health():
    return {"status": "ok", "endpoint": "ranking"}
