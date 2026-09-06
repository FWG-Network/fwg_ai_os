from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import api_router
from backend.api.endpoints.os import router as os_router
from backend.api.endpoints.nexus import router as nexus_router
from backend.core.config import settings
from backend.core.logger import log

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
app.include_router(nexus_router, prefix="/api/v1")
app.include_router(os_router)


@app.on_event("startup")
def recover_interrupted_goals() -> None:
    from backend.models.db import SessionLocal, init_db, mark_interrupted_goals_failed

    try:
        init_db()
        db = SessionLocal()
        try:
            recovered = mark_interrupted_goals_failed(db)
            if recovered:
                log.warning(f"[AIOS] Marked {recovered} interrupted goal(s) as failed")
        finally:
            db.close()
    except Exception as e:
        log.error(f"[AIOS] Startup recovery failed: {e}")


@app.get("/")
def root():
    return {
        "system": settings.APP_NAME,
        "status": "online",
        "version": "4.0",
        "architecture_phase": 30,
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "4.0",
    }
