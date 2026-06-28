from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from backend.models.schemas import DiscoveryRequest
from backend.models.db import get_db
from backend.services.ranking_engine import ranking_engine_service
from backend.core.logger import log

router = APIRouter(prefix="/discovery", tags=["Discovery"])


# ─── POST /discovery/discover ─────────────────────────────────────────
@router.post("/discover")
async def run_discovery_pipeline(
    request: DiscoveryRequest,
    mode: Literal["simple", "smart"] = Query(
        default="smart",
        description="simple=direct search | smart=competitor analysis + DB persist"
    ),
    db: Session = Depends(get_db),
):
    """
    Discovery + Ranking pipeline.

    **mode=simple** — direct search (fast, no DB)
    **mode=smart**  — reverse-engineer creator credits
                      from competitor channels (Oogway Ranks etc.)
    """
    log.info(f"[Discovery] mode={mode} topic='{request.topic}' user='{request.user_id}'")

    # ── SMART MODE (V1) ───────────────────────────────────────────────
    if mode == "smart":
        try:
            from backend.services.discovery_engine import discovery_engine_service
            result = await discovery_engine_service.smart_discover(request.topic, db)

            # ✅ V3: await async rank
            ranked = await ranking_engine_service.rank(
                result.get("trending_candidates", []),
                user_id=request.user_id,
            )

            return {
                "mode":                      "smart",
                "ranked_content":            ranked,
                "source_creators_found":     result.get("source_creators_found", []),
                "matched_competitor_videos": result.get("matched_competitor_videos", []),
                "platforms_scanned":         result.get("platforms_scanned", []),
                "platforms_pending":         result.get("platforms_pending", []),
                "total":                     len(ranked),
            }

        except Exception as e:
            log.warning(f"[Discovery] Smart mode failed → fallback simple: {e}")
            # ✅ Fallback to simple if smart fails
            mode = "simple"

    # ── SIMPLE MODE (V2+V3) ───────────────────────────────────────────
    try:
        from backend.services.discovery_engine import discovery_engine_service
        candidates = await discovery_engine_service.discover(request.topic)
    except Exception as e:
        log.warning(f"[Discovery] Engine failed: {e}")
        candidates = []

    ranked = await ranking_engine_service.rank(
        candidates,
        user_id=request.user_id,
    )

    return {
        "mode":            "simple",
        "ranked_content":  ranked,
        "total":           len(ranked),
    }


# ─── GET /discovery/health ────────────────────────────────────────────
@router.get("/health")
async def discovery_health():
    return {"status": "ok", "endpoint": "discovery"}
