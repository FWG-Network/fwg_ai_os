"""
Discovery Engine — Multi-platform content discovery.

Flow:
  simple → YouTube search (topic + modifiers) → cache → return
  smart  → PolarRanks/Oogway scan → extract creators
         → search creators' videos → merge with topic search → return
"""
import asyncio
import json
from typing import Dict, List, Optional

import redis
from sqlalchemy.orm import Session

from backend.services.connectors.youtube import youtube_connector
from backend.services.connectors.apify import tiktok_connector
from backend.core.config import settings
from backend.core.logger import log


MODIFIERS = ["viral", "shocking", "epic", "new"]

PLATFORMS_AVAILABLE = ["youtube", "tiktok"]
PLATFORMS_PENDING   = [
    "reddit (Devvit Developer Platform registration required)",
]

CACHE_TTL_SECONDS = 3600   # 1 hour


class DiscoveryEngine:

    def __init__(self):
        self._redis_client = None   # lazy — fork-safe

    # ─── Redis (consistent with PersonalizationEngine) ────────────────
    def _get_redis(self) -> Optional[redis.Redis]:
        if self._redis_client is None:
            try:
                # ✅ Fix 3: use REDIS_URL (consistent with personalization)
                self._redis_client = redis.from_url(
                    settings.REDIS_URL,
                    db=2,                    # db=2 = discovery namespace
                    decode_responses=True,
                    socket_timeout=3,
                )
                self._redis_client.ping()
                log.info("[DiscoveryEngine] ✅ Redis connected (db=2)")
            except Exception as e:
                log.error(f"[DiscoveryEngine] Redis unavailable: {e}")
                self._redis_client = False   # mark as failed
        return self._redis_client or None

    # ─── Build search queries ─────────────────────────────────────────
    def _build_queries(self, topic: str) -> List[str]:
        queries = [topic]
        for modifier in MODIFIERS:
            queries.append(f"{modifier} {topic}")
        return list(set(queries))

    # ─── SIMPLE DISCOVER ─────────────────────────────────────────────
    async def discover(
        self,
        topic:           str,
        limit_per_query: int = 5,
    ) -> List[Dict]:
        """
        Direct YouTube search with topic + modifiers.
        Redis cached for 1 hour.
        """
        cache_key = f"discovery:{topic}:{limit_per_query}"
        r         = self._get_redis()

        # ── Cache read ───────────────────────────────────────────────
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    log.info(f"[DiscoveryEngine] Cache hit: '{topic}'")
                    return json.loads(cached)
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Cache read failed: {e}")

        # ── Search ───────────────────────────────────────────────────
        queries       = self._build_queries(topic)
        all_candidates: List[Dict] = []

        for query in queries:
            try:
                results = await youtube_connector.search(
                    query, limit=limit_per_query
                )
                all_candidates.extend(results)
                log.info(f"[DiscoveryEngine] '{query}' → {len(results)} results")
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Query '{query}' failed: {e}")
                continue

            await asyncio.sleep(0.5)   # rate limit between queries

        # ── Deduplicate ──────────────────────────────────────────────
        seen: set      = set()
        deduped: List[Dict] = []
        for item in all_candidates:
            if item["id"] not in seen:
                seen.add(item["id"])
                deduped.append(item)

        log.info(f"[DiscoveryEngine] discover: {len(deduped)} unique results for '{topic}'")

        # ── Cache write ──────────────────────────────────────────────
        if r:
            try:
                r.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(deduped))
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Cache write failed: {e}")

        return deduped

    # ─── SMART DISCOVER ──────────────────────────────────────────────
    async def smart_discover(
        self,
        topic: str,
        db:    Session,
    ) -> Dict:
        """
        Smart multi-step discovery:
        1. Scan PolarRanks/Oogway → extract credited @creators
        2. Search those creators' videos about topic  ← ✅ Fix 2
        3. Merge with direct topic search             ← ✅ Fix 1
        """
        log.info(f"[DiscoveryEngine] smart_discover: '{topic}'")

        # ── Step 1: Competitor channel scan ──────────────────────────
        competitor_result = await youtube_connector.suggest_from_known_channels(
            db=db,
            theme_keyword=topic,
        )
        creators_ranked = competitor_result.get("source_creators_ranked", [])
        log.info(f"[DiscoveryEngine] Found {len(creators_ranked)} credited creators")

        # ── Step 2: Search credited creators' videos  ✅ Fix 2 ───────
        creator_candidates: List[Dict] = []
        for handle, mention_count in creators_ranked[:5]:   # top 5 creators
            try:
                results = await youtube_connector.search(
                    query=f"{topic} {handle}",
                    limit=3,
                )
                # tag with creator source
                for r in results:
                    r["credited_by"] = handle
                    r["mention_count"] = mention_count
                creator_candidates.extend(results)
                log.info(f"[DiscoveryEngine] Creator @{handle}: {len(results)} videos")
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Creator search @{handle} failed: {e}")
            await asyncio.sleep(0.3)

        # ── Step 3: Topic-filtered trending  ✅ Fix 1 ────────────────
        # search trending ដែល filter by topic — មិនមែន generic trending
        try:
            topic_trending = await youtube_connector.search(
                query=f"{topic} trending",
                limit=10,
                min_views=10000,
            )
            log.info(f"[DiscoveryEngine] Topic trending: {len(topic_trending)} videos")
        except Exception as e:
            log.warning(f"[DiscoveryEngine] Topic trending failed: {e}")
            topic_trending = []

        # ── Merge + Deduplicate ───────────────────────────────────────
        all_candidates = creator_candidates + topic_trending
        seen: set      = set()
        deduped: List[Dict] = []
        for item in all_candidates:
            if item["id"] not in seen:
                seen.add(item["id"])
                deduped.append(item)

        log.info(
            f"[DiscoveryEngine] smart_discover complete: "
            f"{len(deduped)} candidates "
            f"({len(creator_candidates)} from creators + "
            f"{len(topic_trending)} from trending)"
        )

        return {
            "topic":                     topic,
            "trending_candidates":       deduped,
            "source_creators_found":     creators_ranked,
            "matched_competitor_videos": competitor_result.get("matched_videos", []),
            "platforms_scanned":         PLATFORMS_AVAILABLE,
            "platforms_pending":         PLATFORMS_PENDING,
            "stats": {
                "creator_videos":  len(creator_candidates),
                "trending_videos": len(topic_trending),
                "total_unique":    len(deduped),
            },
        }



    # ── Phase 1D: SourceHunterAgent execution layer ─────────────
    async def discover_from_strategy(self, query: str, filters: dict | None = None, platform: str = "youtube") -> list[dict]:
        """
        Execute a single search query (already resolved by SourceHunterAgent
        from a PlatformStrategy's primary_queries/keywords) against YouTube
        or TikTok, reusing existing cache + dedup pattern where applicable.
        Returns raw connector results (list[dict], same shape as
        discover()/smart_discover() candidates).
        """
        filters = filters or {}

        if platform == "tiktok":
            try:
                results = await tiktok_connector.search(query, limit=10)
            except Exception as e:
                log.error(f"[DiscoveryEngine] TikTok strategy search failed for '{query}': {e}")
                return []
            log.info(f"[DiscoveryEngine] discover_from_strategy: {len(results)} TikTok results for '{query}'")
            return results

        cache_key = f"discovery:strategy:{query}"
        r = self._get_redis()

        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    log.info(f"[DiscoveryEngine] Strategy cache hit: '{query}'")
                    return json.loads(cached)
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Strategy cache read failed: {e}")

        try:
            search_kwargs = {"min_views": filters.get("min_views", 0), "exclude_reposts": True}
            if "days_ago_start" in filters:
                search_kwargs["days_ago_start"] = filters["days_ago_start"]
            if "days_ago_end" in filters:
                search_kwargs["days_ago_end"] = filters["days_ago_end"]
            if "region_code" in filters:
                search_kwargs["region_code"] = filters["region_code"]
            if "relevance_language" in filters:
                search_kwargs["relevance_language"] = filters["relevance_language"]

            results = await youtube_connector.search(query, **search_kwargs)
        except Exception as e:
            log.error(f"[DiscoveryEngine] Strategy search failed for '{query}': {e}")
            return []

        if r:
            try:
                r.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(results))
            except Exception as e:
                log.warning(f"[DiscoveryEngine] Strategy cache write failed: {e}")

        log.info(f"[DiscoveryEngine] discover_from_strategy: {len(results)} results for '{query}'")
        return results


discovery_engine_service = DiscoveryEngine()
