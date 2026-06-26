# backend/services/connectors/youtube.py
import re
import httpx
from datetime import datetime, timedelta
from backend.core.config import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

REPOST_KEYWORDS = ["compilation", "reaction to", "react to", "reupload", "best of"]
CREDIT_HANDLE_PATTERN = re.compile(r'@[\w.]+')

# ★ List channel ល្បីៗ — append បន្ថែមបានពេលរកឃើញ channel ថ្មីក្នុង niche
KNOWN_RANKING_CHANNELS = ["PolarRanks", "oogway_ranks", "mrpurifiedwater"]


class YouTubeConnector:

    def __init__(self):
        self._channel_id_cache: dict[str, str | None] = {}  # សន្សំ quota — resolve ម្តងគត់

    # ==========================================================
    # Shared helpers
    # ==========================================================
    async def _resolve_channel_id(self, client: httpx.AsyncClient, handle: str) -> str | None:
        if handle in self._channel_id_cache:
            return self._channel_id_cache[handle]
        resp = await client.get(CHANNELS_URL, params={
            "part": "id", "forHandle": handle, "key": settings.YOUTUBE_API_KEY,
        })
        resp.raise_for_status()
        items = resp.json().get("items", [])
        channel_id = items[0]["id"] if items else None
        self._channel_id_cache[handle] = channel_id
        return channel_id

    def _build_results(self, items, detail_map, min_views, exclude_reposts) -> list[dict]:
        results = []
        for item in items:
            raw_id = item["id"]
            vid = raw_id["videoId"] if isinstance(raw_id, dict) else raw_id
            detail = detail_map.get(vid, {})
            snippet = detail.get("snippet", item.get("snippet", {}))
            stats = detail.get("statistics", {})
            title = snippet.get("title", "")
            views = int(stats.get("viewCount", 0))
            likes = int(stats.get("likeCount", 0))

            if views < min_views:
                continue
            if exclude_reposts and any(k in title.lower() for k in REPOST_KEYWORDS):
                continue

            results.append({
                "id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": title,
                "platform": "youtube",
                "channel": snippet.get("channelTitle"),
                "tags": snippet.get("tags", []),
                "views": views,
                "likes": likes,
                "engagement_rate": round(likes / views, 4) if views else 0,
                "published_at": snippet.get("publishedAt"),
            })
        results.sort(key=lambda r: r["engagement_rate"], reverse=True)
        return results

    # ==========================================================
    # OPTION 1 — Search ខ្លួនឯង (ដឹង keyword ច្បាស់ៗ, cost: 100 units)
    # ==========================================================
    async def search(
        self, query: str, limit: int = 10,
        days_ago_start: int = 7, days_ago_end: int = 0,
        min_views: int = 0, exclude_reposts: bool = True,
        region_code: str | None = None, relevance_language: str | None = None,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            print("⚠️ WARNING: YOUTUBE_API_KEY not set. Mock data returned.")
            return []

        limit = min(limit, 50)
        start_time = datetime.utcnow() - timedelta(days=days_ago_start)
        end_time = datetime.utcnow() - timedelta(days=days_ago_end)
        params = {
            "part": "snippet", "q": query, "key": settings.YOUTUBE_API_KEY,
            "maxResults": limit, "type": "video", "order": "viewCount",
            "publishedAfter": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "publishedBefore": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        if region_code:
            params["regionCode"] = region_code
        if relevance_language:
            params["relevanceLanguage"] = relevance_language

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(SEARCH_URL, params=params)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    return []
                video_ids = ",".join(i["id"]["videoId"] for i in items)
                detail_resp = await client.get(VIDEOS_URL, params={
                    "part": "snippet,statistics", "id": video_ids,
                    "key": settings.YOUTUBE_API_KEY,
                })
                detail_resp.raise_for_status()
                detail_map = {v["id"]: v for v in detail_resp.json().get("items", [])}
                return self._build_results(items, detail_map, min_views, exclude_reposts)
            except Exception as e:
                print(f"❌ ERROR search(): {e}")
                return []

    # ==========================================================
    # OPTION 2 — Trending (មិនបាច់ដឹង keyword, cost: 1 unit ប៉ុណ្ណោះ)
    # ==========================================================
    async def get_trending(
        self, region_code: str = "US", category_id: str = "24",
        limit: int = 25, min_views: int = 0, exclude_reposts: bool = True,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            return []
        params = {
            "part": "snippet,statistics", "chart": "mostPopular",
            "regionCode": region_code, "videoCategoryId": category_id,
            "maxResults": min(limit, 50), "key": settings.YOUTUBE_API_KEY,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                resp = await client.get(VIDEOS_URL, params=params)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                detail_map = {v["id"]: v for v in items}
                fake_items = [{"id": v["id"], "snippet": v["snippet"]} for v in items]
                return self._build_results(fake_items, detail_map, min_views, exclude_reposts)
            except Exception as e:
                print(f"❌ ERROR get_trending(): {e}")
                return []

    # ==========================================================
    # OPTION 3 — Smart Suggest (auto-check channel ល្បីៗ + extract credit)
    # ★ ដោះស្រាយ "មិនដឹងថា search ត្រូវ keyword អ្វី" ដោយផ្ទាល់
    # ==========================================================
    async def suggest_from_known_channels(
        self,
        theme_keyword: str,
        channels: list[str] | None = None,   # None = ប្រើ KNOWN_RANKING_CHANNELS
        videos_per_channel: int = 5,
    ) -> dict:
        if not settings.YOUTUBE_API_KEY:
            return {"matched_videos": [], "source_creators_ranked": []}

        channels = channels or KNOWN_RANKING_CHANNELS
        all_matched_videos = []
        handle_counts: dict[str, int] = {}

        async with httpx.AsyncClient(timeout=15) as client:
            for handle in channels:
                try:
                    channel_id = await self._resolve_channel_id(client, handle)
                    if not channel_id:
                        print(f"⚠️ Channel not found: {handle}")
                        continue

                    search_resp = await client.get(SEARCH_URL, params={
                        "part": "snippet", "channelId": channel_id, "q": theme_keyword,
                        "type": "video", "maxResults": videos_per_channel,
                        "key": settings.YOUTUBE_API_KEY,
                    })
                    search_resp.raise_for_status()
                    videos = search_resp.json().get("items", [])
                    if not videos:
                        continue

                    video_ids = ",".join(v["id"]["videoId"] for v in videos)
                    detail_resp = await client.get(VIDEOS_URL, params={
                        "part": "snippet", "id": video_ids, "key": settings.YOUTUBE_API_KEY,
                    })
                    detail_resp.raise_for_status()

                    for v in detail_resp.json().get("items", []):
                        desc = v["snippet"].get("description", "")
                        handles = CREDIT_HANDLE_PATTERN.findall(desc)
                        all_matched_videos.append({
                            "source_channel": handle,
                            "title": v["snippet"]["title"],
                            "url": f"https://www.youtube.com/watch?v={v['id']}",
                            "credited_handles": handles,
                        })
                        for h in handles:
                            handle_counts[h] = handle_counts.get(h, 0) + 1
                except Exception as e:
                    print(f"❌ ERROR checking channel {handle}: {e}")
                    continue

        return {
            "matched_videos": all_matched_videos,
            "source_creators_ranked": sorted(handle_counts.items(), key=lambda x: x[1], reverse=True),
            "channels_checked": channels,
        }


youtube_connector = YouTubeConnector()
