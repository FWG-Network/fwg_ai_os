"""
TikTok discovery via Apify's clockworks/tiktok-scraper actor.

Phase 6A contract (VOF-approved):
- observed_metrics preserves TikTok-native field names exactly
  (playCount, diggCount, shareCount, commentCount, collectCount) —
  NEVER renamed/converted to views/likes at this layer.
- Legacy views/likes/engagement_rate are left None (not 0) since
  TikTok data doesn't map 1:1 to those YouTube-native concepts.
- This connector does NOT rank, score, or judge clips — pure
  discovery + normalization only.
- Failures are caught and logged; never raised — a TikTok failure
  must not crash a mission that also has YouTube results.
"""
import httpx
from backend.core.config import settings

APIFY_RUN_SYNC_URL = "https://api.apify.com/v2/acts/clockworks~tiktok-scraper/run-sync-get-dataset-items"

# Fields verified live (Phase 6A Step 3 evidence report) — only these
# are ever written into observed_metrics. No fabrication of others.
_OBSERVED_METRIC_KEYS = ("playCount", "diggCount", "shareCount", "commentCount", "collectCount")


class TikTokConnector:
    def _build_results(self, items: list[dict]) -> list[dict]:
        results = []
        for item in items:
            observed_metrics = {}
            for key in _OBSERVED_METRIC_KEYS:
                if key in item and item[key] is not None:
                    observed_metrics[key] = item[key]

            author_meta = item.get("authorMeta")
            channel = author_meta.get("name", "") if isinstance(author_meta, dict) else ""

            hashtags = item.get("hashtags") or []
            tags = [h.get("name", "") for h in hashtags if isinstance(h, dict)]

            results.append({
                "id": item.get("id", ""),
                "url": item.get("webVideoUrl", ""),
                "title": item.get("text", ""),
                "platform": "tiktok",
                "channel": channel,
                "tags": tags,
                "views": None,
                "likes": None,
                "engagement_rate": None,
                "published_at": item.get("createTimeISO"),
                "observed_metrics": observed_metrics,
                "metric_schema_version": "tiktok_v1",
            })
        return results

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        if not settings.APIFY_API_TOKEN:
            print("⚠️ WARNING: APIFY_API_TOKEN not set. No TikTok results returned.")
            return []

        params = {"token": settings.APIFY_API_TOKEN}
        payload = {
            "searchQueries": [query],
            "resultsPerPage": limit,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(APIFY_RUN_SYNC_URL, params=params, json=payload)
                resp.raise_for_status()
                items = resp.json()
                if not isinstance(items, list):
                    print(f"⚠️ WARNING: TikTok search unexpected response shape: {type(items)}")
                    return []
                return self._build_results(items)
            except Exception as e:
                print(f"❌ ERROR TikTokConnector.search(): {e}")
                return []


tiktok_connector = TikTokConnector()
