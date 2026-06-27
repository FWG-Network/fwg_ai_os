from fastapi import APIRouter
from backend.models.schemas import DiscoveryRequest
from backend.services.discovery_engine import discovery_engine_service
from backend.services.ranking_engine import ranking_engine_service
from backend.core.logger import log

router = APIRouter()

@router.post("/discover")
async def run_discovery_pipeline(request: DiscoveryRequest):
    """
    Runs the full discovery and ranking pipeline.
    """
    log.info(f"Discovery pipeline: topic='{request.topic}' user='{request.user_id}'")

    # 1. Discover candidates
    candidates = await discovery_engine_service.discover(request.topic)

    # 2. Rank + personalize (pass user_id, not user_profile dict)
    ranked_candidates = ranking_engine_service.rank(
        candidates,
        user_id=request.user_id  # ✅ str | None
    )

    # 3. Consistent response format
    return {"ranked_content": ranked_candidates}
    
# backend/api/endpoints/discovery.py
@router.post("/discover")
async def run_discovery_pipeline(request: DiscoveryRequest):
    candidates = await discovery_engine_service.discover(request.topic)

    # ✅ await ព្រោះ rank() ជា async ហើយ
    ranked = await ranking_engine_service.rank(
        candidates,
        user_id=request.user_id,
    )
    return {"ranked_content": ranked}
