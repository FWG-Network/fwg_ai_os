from fastapi import APIRouter
from backend.api.endpoints import (
    discovery,
    feedback,
    ranking,
    llm,
    multimodal,
    os as os_ep,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(discovery.router)
api_router.include_router(feedback.router)
api_router.include_router(ranking.router)
api_router.include_router(llm.router)
api_router.include_router(multimodal.router)
api_router.include_router(os_ep.router)
