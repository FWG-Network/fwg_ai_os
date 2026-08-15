from fastapi import APIRouter

router = APIRouter(
    prefix="/nexus",
    tags=["Nexus"],
)


@router.get("/health")
async def nexus_health():
    return {
        "status": "ok",
        "service": "nexus",
    }
