from fastapi import FastAPI
from backend.api.router import api_router
from backend.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="4.0",
    description="Autonomous Intelligence Operating System"
)

app.include_router(api_router)

@app.get("/")
def root():
    return {
        "system": settings.APP_NAME,
        "status": "online",
        "architecture_phase": 30
    }

# To run this: uvicorn backend.main:app --reload
