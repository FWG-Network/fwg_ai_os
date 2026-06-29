from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from backend.core.logger import log

router = APIRouter(prefix="/multimodal", tags=["Multimodal"])


class MultimodalRequest(BaseModel):
    text:      Optional[str] = None
    image_url: Optional[str] = None
    task:      str           = "analyze"


@router.post("/analyze")
async def analyze(request: MultimodalRequest):
    """Analyze text/image with multimodal engine."""
    log.info(f"[Multimodal] task={request.task}")
    try:
        from backend.services.multimodal_engine import multimodal_engine_service
        result = await multimodal_engine_service.analyze(
            text=request.text,
            image_url=request.image_url,
            task=request.task,
        )
        return {"result": result, "task": request.task}
    except Exception as e:
        log.error(f"[Multimodal] Error: {e}")
        raise HTTPException(500, f"Multimodal failed: {e}")


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Upload image for analysis."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(422, "File must be an image")
    content = await file.read()
    log.info(f"[Multimodal] Upload: {file.filename} ({len(content)} bytes)")
    return {"filename": file.filename, "size": len(content), "status": "uploaded"}


@router.get("/health")
async def multimodal_health():
    return {"status": "ok", "endpoint": "multimodal"}
