from fastapi import APIRouter
from backend.models.schemas import DiscoveryRequest # Assume this schema exists
from backend.services.discovery_engine import discovery_engine_service
from backend.services.ranking_engine import ranking_engine_service
# Import personalization and user profile logic when ready

router = APIRouter()

@router.post("/discover")
async def run_discovery_pipeline(request: DiscoveryRequest):
    """
    Runs the full discovery and ranking pipeline.
    """
    # 1. Discover candidates from various sources
    candidates = await discovery_engine_service.discover(request.topic)
    
    # 2. Rank the discovered candidates (user_profile is mock for now)
    user_profile = {"interests": {request.topic: 5}} 
    ranked_candidates = ranking_engine_service.rank(candidates, user_profile)
    
    # 3. Personalize (in the future)
    
    return ranked_candidates
