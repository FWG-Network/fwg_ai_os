# backend/services/connectors/youtube.py
import httpx
from datetime import datetime, timedelta
from backend.core.config import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"  # ប្រើទាំង detail fetch និង trending

# Heuristic — exclude title keyword ដែលច្រើនជា repost/compilation (មិនមែន original)
REPOST_KEYWORDS = ["compilation", "reaction to", "react to", "reupload", "best of"]


class YouTubeConnector:

    # ==========================================================
    # METHOD 1: Keyword Search (cost: 100 units/call)
    # ប្រើពេលដឹង exact topic/keyword ច្បាស់ៗ
    # ==========================================================
    async def search(
        self,
        query: str,
        limit: int = 10,
        days_ago_start: int = 7,
        days_ago_end: int = 0,
        min_views: int = 0,
        exclude_reposts: bool = True,
        region_code: str | None = None,        # កុំដាក់ "KH" បើចង់ content អន្តរជាតិ
        relevance_language: str | None = None,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            print("⚠️ WARNING: YOUTUBE_API_KEY not set. Returning mock data.")
            return [{"id": f"yt_mock_{query.replace(' ','_')}", "url": "", "title": f"Mock: {query}",
                     "platform": "youtube", "tags": [], "views": 0, "engagement_rate": 0,
                     "published_at": datetime.utcnow().isoformat()}]

        limit = min(limit, 50)  # YouTube hard cap — ការពារ error 400
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
                print(f"📡 YouTubeConnector.search: '{query}'...")
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

            except httpx.HTTPStatusError as e:
                print(f"❌ ERROR: {e.response.status_code} {e.response.text}")
                return []
            except Exception as e:
                print(f"❌ ERROR: {e}")
                return []

    # ==========================================================
    # METHOD 2: Trending Discovery (cost: 1 unit/call — 100x cheaper!)
    # ប្រើពេលមិនដឹង exact keyword — ចង់ឃើញ "moment ប្លែកៗ" ប្រចាំថ្ងៃ
    # ==========================================================
    async def get_trending(
        self,
        region_code: str = "US",       # international content
        category_id: str = "24",       # 24 = Entertainment, 20 = Gaming
        limit: int = 25,
        min_views: int = 0,
        exclude_reposts: bool = True,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            print("⚠️ WARNING: YOUTUBE_API_KEY not set. Returning mock data.")
            return []

        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "videoCategoryId": category_id,
            "maxResults": min(limit, 50),
            "key": settings.YOUTUBE_API_KEY,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            try:
                print(f"📡 YouTubeConnector.get_trending: region={region_code}, category={category_id}...")
                resp = await client.get(VIDEOS_URL, params=params)
                resp.raise_for_status()
                items = resp.json().get("items", [])
                if not items:
                    return []

                # chart=mostPopular ផ្ទាល់ផ្តល់ snippet+statistics ស្រេច — មិនបាច់ហៅ detail ម្តងទៀត
                detail_map = {v["id"]: v for v in items}
                fake_search_items = [{"id": {"videoId": v["id"]}, "snippet": v["snippet"]} for v in items]

                return self._build_results(fake_search_items, detail_map, min_views, exclude_reposts)

            except httpx.HTTPStatusError as e:
                print(f"❌ ERROR: {e.response.status_code} {e.response.text}")
                return []
            except Exception as e:
                print(f"❌ ERROR: {e}")
                return []

    # ==========================================================
    # Shared helper — transform raw API items ទៅ internal format
    # ==========================================================
    def _build_results(self, items, detail_map, min_views, exclude_reposts) -> list[dict]:
        results = []
        for item in items:
            vid = item["id"]["videoId"]
            detail = detail_map.get(vid, {})
            snippet = detail.get("snippet", item["snippet"])
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


youtube_connector = YouTubeConnector()
