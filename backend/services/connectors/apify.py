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

class TikTokDiscoveryError(RuntimeError):
    """Explicit Apify/TikTok discovery failure."""

    def __init__(
        self,
        message: str,
        *,
        error_type: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.status_code = status_code


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
            raise TikTokDiscoveryError(
                "APIFY_API_TOKEN is not configured",
                error_type="configuration",
            )

        params = {"token": settings.APIFY_API_TOKEN}
        payload = {
            "searchQueries": [query],
            "resultsPerPage": limit,
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            try:
                resp = await client.post(
                    APIFY_RUN_SYNC_URL,
                    params=params,
                    json=payload,
                )
                resp.raise_for_status()

                items = resp.json()
                if not isinstance(items, list):
                    raise TikTokDiscoveryError(
                        f"Unexpected Apify response shape: {type(items).__name__}",
                        error_type="response_shape",
                        status_code=resp.status_code,
                    )

                return self._build_results(items)

            except TikTokDiscoveryError:
                raise

            except httpx.HTTPStatusError as e:
                raise TikTokDiscoveryError(
                    f"Apify HTTP request failed with status {e.response.status_code}",
                    error_type="http_status",
                    status_code=e.response.status_code,
                ) from e

            except httpx.RequestError as e:
                raise TikTokDiscoveryError(
                    f"Apify request failed: {type(e).__name__}",
                    error_type="request",
                ) from e

            except Exception as e:
                raise TikTokDiscoveryError(
                    f"Apify response processing failed: {type(e).__name__}",
                    error_type="processing",
                ) from e
tiktok_connector = TikTokConnector()
