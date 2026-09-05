from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Literal

from backend.models.schemas import DiscoveryRequest
from backend.models.db import get_db
from backend.services.ranking_engine import ranking_engine_service
from backend.services.intelligence_engine import intelligence_engine_service
from backend.services.evaluation_engine import evaluation_engine_service
from backend.core.logger import log

router = APIRouter(prefix="/discovery", tags=["Discovery"])


# ─── POST /discovery/discover ─────────────────────────────────────────
@router.post("/discover")
async def run_discovery_pipeline(
    request: DiscoveryRequest,
    mode: Literal["simple", "smart"] = Query(
        default="smart",
        description="simple=direct | smart=PolarRanks competitor analysis"
    ),
    db: Session = Depends(get_db),
):
    """
    Discovery + Ranking pipeline.

    **mode=smart**  — scan PolarRanks/Oogway → extract creators → rank
    **mode=simple** — direct YouTube search → rank
    """
    log.info(f"[Discovery] mode={mode} topic='{request.topic}' user='{request.user_id}'")

    # ── SMART MODE — PolarRanks competitor analysis ───────────────────
    if mode == "smart":
        try:
            from backend.services.discovery_engine import discovery_engine_service
            result = await discovery_engine_service.smart_discover(request.topic, db)

            # ✅ rank() is sync — NO await
            candidates = result.get("trending_candidates", [])

            enriched = intelligence_engine_service.analyze(
                candidates,
                editorial_intent={
                    "topic": request.topic,
                },
            )
            evaluated = evaluation_engine_service.evaluate(
                enriched,
            )

            ranked = ranking_engine_service.rank(
                evaluated,
                user_id=request.user_id,
            )

            return {
                "mode":                      "smart",
                "topic":                     request.topic,   # ✅ Dev
                "total":                     len(ranked),
                "ranked_content":            ranked,
                "source_creators_found":     result.get("source_creators_found",     []),
                "matched_competitor_videos": result.get("matched_competitor_videos", []),
                "platforms_scanned":         result.get("platforms_scanned",         []),
                "platforms_pending":         result.get("platforms_pending",         []),
            }

        except Exception as e:
            log.warning(f"[Discovery] Smart failed → fallback simple: {e}")
            mode = "simple"  # ✅ explicit fallback

    # ── SIMPLE MODE — direct search ───────────────────────────────────
    try:
        from backend.services.discovery_engine import discovery_engine_service
        candidates = await discovery_engine_service.discover(request.topic)
    except Exception as e:
        log.warning(f"[Discovery] Engine failed: {e}")
        candidates = []

    # ✅ rank() is sync — NO await
    enriched = intelligence_engine_service.analyze(
        candidates,
        editorial_intent={
            "topic": request.topic,
        },
    )
    evaluated = evaluation_engine_service.evaluate(
        enriched,
    )

    ranked = ranking_engine_service.rank(
        evaluated,
        user_id=request.user_id,
    )

    return {
        "mode":           "simple",
        "topic":          request.topic,   # ✅ Dev
        "total":          len(ranked),
        "ranked_content": ranked,
    }


# ─── GET /discovery/health ────────────────────────────────────────────
@router.get("/health")
async def discovery_health():
    return {"status": "ok", "endpoint": "discovery"}
