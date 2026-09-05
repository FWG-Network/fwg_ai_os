"""
backend/services/ranking_engine.py
Multi-factor weighted ranking engine.
"""
from math import log as math_log
from typing import Optional

from backend.core.logger import log


class RankingEngine:

    WEIGHTS = {
        "semantic":        0.40,
        "popularity":      0.20,
        "engagement":      0.15,
        "freshness":       0.15,
        "personalization": 0.10,   # total = 1.0 ✅
    }

    def rank(
        self,
        candidates: list[dict],
        user_id:    Optional[str] = None,
    ) -> list[dict]:
        log.info(f"[Ranking] {len(candidates)} candidates user='{user_id}'")

        ranked = []
        for item in candidates:
            scores = self._score_components(item, user_id)
            final  = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
            ranked.append({
                **item,
                "score":        round(final, 6),
                "_score_debug": scores,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    def _score_components(
        self,
        item:    dict,
        user_id: Optional[str],
    ) -> dict[str, float]:
        views    = item.get("views")
        likes    = item.get("likes")
        age_days = item.get("age_days")
        semantic = item.get("semantic_score", 0.8)

        pop = (
            min(math_log(float(views) + 1.0) / 10.0, 1.0)
            if isinstance(views, (int, float)) and views >= 0
            else 0.0
        )
        eng = (
            min(float(likes) / float(views), 1.0)
            if (
                isinstance(likes, (int, float))
                and isinstance(views, (int, float))
                and views > 0
            )
            else 0.0
        )
        fresh = (
            max(0.0, 1.0 - float(age_days) / 365.0)
            if isinstance(age_days, (int, float)) and age_days >= 0
            else 0.0
        )

        # ✅ Fix: try/except — personalization never crashes ranking
        personal = 0.0
        if user_id:
            try:
                from backend.services.personalization_engine import (
                    personalization_engine_service,
                )
                raw      = personalization_engine_service.get_personalization_bonus(item, user_id)
                personal = max(0.0, min(raw, 1.0))
            except Exception as e:
                log.warning(f"[Ranking] Personalization skipped: {e}")

        return {
            "semantic":        float(semantic or 0.0),
            "popularity":      pop,
            "engagement":      eng,
            "freshness":       fresh,
            "personalization": personal,
        }


ranking_engine_service = RankingEngine()
