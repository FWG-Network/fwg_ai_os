# backend/api/router.py

from fastapi import APIRouter
# 🚀 TREND FORECASTER UPGRADE: Import the new trends endpoint
from backend.api.endpoints import discovery, ranking, feedback, llm, os, memory, trends

api_router = APIRouter()

# API v1 Routes
api_router.include_router(discovery.router, prefix="/v1/discovery", tags=["Discovery Engine"])
api_router.include_router(ranking.router, prefix="/v1/ranking", tags=["Ranking Engine"])
api_router.include_router(feedback.router, prefix="/v1/feedback", tags=["Learning System"])
api_router.include_router(llm.router, prefix="/v1/llm", tags=["LLM Brain"])
api_router.include_router(os.router, prefix="/v1/os", tags=["Autonomous OS"])
api_router.include_router(memory.router, prefix="/v1/memory", tags=["Knowledge Base"])

# 🚀 TREND FORECASTER UPGRADE: Activate the new trends API
api_router.include_router(trends.router, prefix="/v1/trends", tags=["Trend Forecaster"])
