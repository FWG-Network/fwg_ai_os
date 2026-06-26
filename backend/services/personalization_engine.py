# backend/services/personalization_engine.py
from backend.core.config import settings
from backend.core.logger import log
import redis


class PersonalizationEngine:
    def __init__(self):
        self._redis_client = None  # ★ lazy — មិន connect ត្រង់ __init__ (fork-safe)

    def _get_client(self):
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST, port=6379, db=1, decode_responses=True
                )
                self._redis_client.ping()
            except redis.exceptions.ConnectionError as e:
                log.error(f"Redis unavailable: {e}", component="PersonalizationEngine")
                self._redis_client = False
        return self._redis_client or None

    def get_user_profile(self, user_id: str) -> dict:
        client = self._get_client()
        if not client or not user_id:
            return {}
        try:
            return client.hgetall(f"user_profile:{user_id}")
        except Exception as e:
            log.exception("Profile fetch failed.", component="PersonalizationEngine", error=str(e))
            return {}

    def _calculate_bonus(self, profile: dict, item_tags: list[str]) -> float:
        if not profile:
            return 0.0
        bonus = sum(float(profile[t]) * 0.01 for t in item_tags if t in profile)
        return min(bonus, 0.3)  # ★ cap រក្សា

    def personalize(self, ranked_items: list[dict], user_id: str) -> list[dict]:
        profile = self.get_user_profile(user_id)  # ★ fetch 1 ដងគត់ មិនមែនរាល់ item
        for item in ranked_items:
            bonus = self._calculate_bonus(profile, item.get("tags", []))
            item["final_score"] = item.get("ranking_score", 0.0) + bonus
        ranked_items.sort(key=lambda x: x["final_score"], reverse=True)
        return ranked_items


personalization_engine_service = PersonalizationEngine()


def populate_demo_profile():
    """★ ហៅ explicit ដោយដៃ — មិនមែន auto-run ពេល import"""
    client = personalization_engine_service._get_client()
    if client:
        client.hset("user_profile:dev-user-01", mapping={
            "python": 0.8, "ai": 0.9, "gaming": 0.4, "tutorial": 0.7,
        })

if __name__ == "__main__":
    populate_demo_profile()  # run: python -m backend.services.personalization_engine
