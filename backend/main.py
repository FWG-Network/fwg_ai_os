from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import api_router
from backend.api.endpoints.os import router as os_router
from backend.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="4.0",
    description="Autonomous Intelligence Operating System - Production Ready Blueprint",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
app.include_router(os_router)


@app.get("/")
def root():
    return {
        "system": settings.APP_NAME,
        "status": "online",
        "architecture_phase": 30,
    }
