from fastapi import APIRouter
from backend.api.endpoints import discovery, ranking, feedback, llm, os

api_router = APIRouter()

# ★★★ FIX: Corrected the router prefixes for consistency ★★★
# The prefix should define the resource. The endpoint path ("/") defines the action on that resource.
api_router.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
api_router.include_router(ranking.router, prefix="/v1/ranking", tags=["Ranking"])
api_router.include_router(feedback.router, prefix="/v1/feedback", tags=["Learning"]) # Changed from /learning
api_router.include_router(llm.router, prefix="/v1/llm", tags=["AI Brain"])
api_router.include_router(os.router, prefix="/v1/os", tags=["Autonomous OS"])
