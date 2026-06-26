from math import log as math_log
from datetime import datetime, timezone
from .personalization_engine import personalization_engine_service
from backend.core.logger import log


class RankingEngine:
    WEIGHTS = {
        "semantic":        0.40,
        "popularity":      0.20,
        "engagement":      0.15,
        "freshness":       0.15,
        "personalization": 0.10,  # ✅ fix: total = 1.0
    }

    def rank(
        self,
        candidates: list[dict],
        user_id: str | None = None
    ) -> list[dict]:
        log.info(f"Ranking {len(candidates)} candidates for user='{user_id}'.")

        ranked = []
        for item in candidates:
            scores = self._score_components(item, user_id)
            final  = sum(
                scores[k] * self.WEIGHTS[k]
                for k in self.WEIGHTS
            )
            ranked.append({
                **item,
                "score":        round(final, 6),
                "_score_debug": scores,   # ✅ debug ងាយ inspect
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    # ─────────────────────────────────────────
    def _score_components(
        self,
        item: dict,
        user_id: str | None
    ) -> dict[str, float]:
        views          = item.get("views", 1000)
        likes          = item.get("likes", 100)
        age_days       = item.get("age_days", 10)
        semantic_score = item.get("semantic_score", 0.8)

        pop   = min(math_log(views + 1) / 10.0, 1.0)
        eng   = min(likes / views, 1.0) if views > 0 else 0.0
        fresh = max(0.0, 1.0 - age_days / 365.0)

        # ✅ Personalization clamp ក្នុង [0, 1]
        personal = 0.0
        if user_id:
            raw      = personalization_engine_service.get_personalization_bonus(item, user_id)
            personal = max(0.0, min(raw, 1.0))

        return {
            "semantic":        semantic_score,
            "popularity":      pop,
            "engagement":      eng,
            "freshness":       fresh,
            "personalization": personal,
        }


ranking_engine_service = RankingEngine()
