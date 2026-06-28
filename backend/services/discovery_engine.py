# backend/services/discovery_engine.py
import asyncio
import json
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from backend.services.connectors.youtube import youtube_connector
from backend.core.config import settings
from backend.core.logger import log

import redis

MODIFIERS = ["viral", "shocking", "epic", "new"]

PLATFORMS_AVAILABLE = ["youtube"]
PLATFORMS_PENDING = [
    "tiktok (architecture unresolved — Apify vs HF Space delegation)",
    "reddit (blocked — Devvit Developer Platform registration required)",
]

CACHE_TTL_SECONDS = 3600  # 1 hour


class DiscoveryEngine:

    def __init__(self):
        self._redis_client = None  # ★ FIX 2: lazy — fork-safe, matches PersonalizationEngine

    def _get_redis(self):
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST, port=6379, db=2, decode_responses=True
                )
                self._redis_client.ping()
            except redis.exceptions.ConnectionError as e:
                log.error(f"[DiscoveryEngine] Redis unavailable: {e}")
                self._redis_client = False
        return self._redis_client or None

    def _build_queries(self, topic: str) -> List[str]:  # ★ FIX 3: List[str] type hints
        queries = [topic]
        for modifier in MODIFIERS:
            queries.append(f"{modifier} {topic}")
        return list(set(queries))

    async def discover(self, topic: str, limit_per_query: int = 5) -> List[Dict]:
        cache_key = f"discovery:{topic}:{limit_per_query}"
        r = self._get_redis()

        if r:  # ★ FIX 2: Redis cache, TTL 1hr
            try:
                cached = r.get(cache_key)
                if cached:
                    log.info(f"[DiscoveryEngine] Cache hit for '{topic}'")
                    return json.loads(cached)
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Cache read failed: {e}")

        queries = self._build_queries(topic)
        all_candidates: List[Dict] = []

        for query in queries:
            try:  # ★ FIX 1: try/except per query
                results = await youtube_connector.search(query, limit=limit_per_query)
                all_candidates.extend(results)
            except Exception as e:
                log.warning(f"[Discovery] Query '{query}' failed: {e}")
                continue

            await asyncio.sleep(0.5)  # ★ FIX 4: rate limit between queries

        seen_ids = set()
        deduped: List[Dict] = []
        for item in all_candidates:
            if item["id"] not in seen_ids:
                seen_ids.add(item["id"])
                deduped.append(item)

        if r:
            try:
                r.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(deduped))
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Cache write failed: {e}")

        return deduped

    async def smart_discover(self, topic: str, db: Session) -> Dict:
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
