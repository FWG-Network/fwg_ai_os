from sqlalchemy.orm import Session
from backend.services.connectors.youtube import youtube_connector

MODIFIERS = ["viral", "shocking", "epic", "new"]

PLATFORMS_AVAILABLE = ["youtube"]
PLATFORMS_PENDING = [
    "tiktok (architecture unresolved — Apify vs HF Space delegation)",
    "reddit (blocked — Devvit Developer Platform registration required)",
]


class DiscoveryEngine:

    def _build_queries(self, topic: str) -> list[str]:
        queries = [topic]
        for modifier in MODIFIERS:
            queries.append(f"{modifier} {topic}")
        return list(set(queries))

    async def discover(self, topic: str, limit_per_query: int = 5) -> list[dict]:
        """
        ⚠️ Quota cost ខ្ពស់: topic + 4 modifiers = 5 queries × 100 units = ~500
        units/ការហៅ (free quota ប្រចាំថ្ងៃ = ~20 ការហៅ ប៉ុណ្ណោះ)
        """
        queries = self._build_queries(topic)
        all_candidates = []

        for query in queries:
            results = await youtube_connector.search(query, limit=limit_per_query)
            all_candidates.extend(results)

        seen_ids = set()
        deduped = []
        for item in all_candidates:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                deduped.append(item)

        return deduped

    async def smart_discover(self, topic: str, db: Session) -> dict:
        competitor_result = await youtube_connector.suggest_from_known_channels(
            db=db, theme_keyword=topic,
        )
        trending_result = await youtube_connector.get_trending(
            category_id="24", min_views=10000,
        )

        return {
            "topic": topic,
            "source_creators_found": competitor_result.get("source_creators_ranked", []),
            "matched_competitor_videos": competitor_result.get("matched_videos", []),
            "trending_candidates": trending_result[:10],
            "platforms_scanned": PLATFORMS_AVAILABLE,
            "platforms_pending": PLATFORMS_PENDING,
        }


discovery_engine_service = DiscoveryEngine()
