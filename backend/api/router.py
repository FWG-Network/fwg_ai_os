from fastapi import APIRouter
from backend.api.endpoints import discovery, ranking, feedback, llm, os # <-- Add os

api_router = APIRouter()
api_router.include_router(discovery.router, prefix="/v1", tags=["Discovery"])
api_router.include_router(ranking.router, prefix="/v1", tags=["Ranking"])
api_router.include_router(feedback.router, prefix="/v1", tags=["Learning"])
api_router.include_router(llm.router, prefix="/v1/llm", tags=["AI Brain"])
api_router.include_router(os.router, prefix="/v1/os", tags=["Autonomous OS"]) # <-- Add os router
