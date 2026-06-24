from fastapi import APIRouter
# ★★★ FIX: All endpoint modules now exist and can be imported safely ★★★
from backend.api.endpoints import discovery, ranking, feedback, llm, os

api_router = APIRouter()

api_router.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery"])
api_router.include_router(ranking.router, prefix="/v1/ranking", tags=["Ranking"])
api_router.include_router(feedback.router, prefix="/v1/learning", tags=["Learning"])
api_router.include_router(llm.router, prefix="/v1/llm", tags=["AI Brain"])
api_router.include_router(os.router, prefix="/v1/os", tags=["Autonomous OS"])
