from math import log as math_log  # ← fix conflict
from datetime import datetime, timezone
from .personalization_engine import personalization_engine_service
from backend.core.logger import log  # ← logger

class RankingEngine:
    WEIGHTS = {
        "semantic": 0.40,
        "popularity": 0.20,
        "engagement": 0.15,
        "freshness": 0.15,
    }

    def rank(self, candidates: list[dict], user_id: str | None = None) -> list[dict]:
        log.info(f"Ranking {len(candidates)} candidates for user '{user_id}'.")
        
        ranked_results = []
        for item in candidates:
            # ✅ Base score ពី version ចាស់
            score = self._calculate_base_score(item)
            
            # ✅ Personalization bonus ពី version ថ្មី
            if user_id:
                score += personalization_engine_service.get_personalization_bonus(item, user_id)
            
            ranked_results.append({**item, "score": score})

        ranked_results.sort(key=lambda x: x["score"], reverse=True)
        return ranked_results

    def _calculate_base_score(self, item: dict) -> float:
        # ✅ Logic ពេញលេញពី version ចាស់
        views = item.get('views', 1000)
        likes = item.get('likes', 100)
        age_days = item.get('age_days', 10)
        semantic_score = item.get('semantic_score', 0.8)

        pop = min(math_log(views + 1) / 10.0, 1.0)
        eng = min(likes / views, 1.0) if views > 0 else 0
        fresh = max(0.0, 1.0 - age_days / 365.0)

        return (
            semantic_score * self.WEIGHTS["semantic"] +
            pop * self.WEIGHTS["popularity"] +
            eng * self.WEIGHTS["engagement"] +
            fresh * self.WEIGHTS["freshness"]
        )

ranking_engine_service = RankingEngine()
