# backend/services/connectors/youtube.py

import re
import httpx
from datetime import datetime, timedelta

# 🚀 REFACTORED: Import modern SQLAlchemy components
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.models.db import Creator, CreatorMention
# ===============================================

from backend.core.config import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

# 🚀 REFACTORED: Use the improved, more specific Regex
CREDIT_HANDLE_PATTERN = re.compile(r'@([a-zA-Z0-9_.-]{3,30})')
# ===============================================

REPOST_KEYWORDS = ["compilation", "reaction to", "react to", "reupload", "best of"]
KNOWN_RANKING_CHANNELS = ["PolarRanks", "oogway_ranks", "mrpurifiedwater", "Data Drip"]

class YouTubeConnector:

    def __init__(self):
        self._channel_id_cache: dict[str, str | None] = {}

    # ==========================================================
    # --- UNCHANGED METHODS START HERE ---
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

    async def search(
        self, query: str, limit: int = 10,
        days_ago_start: int = 7, days_ago_end: int = 0,
        min_views: int = 0, exclude_reposts: bool = True,
        region_code: str | None = None, relevance_language: str | None = None,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            print("⚠️ WARNING: YOUTUBE_API_KEY not set. Mock data returned.")
            return []
        # ... (rest of the search method logic is unchanged)
        # ... it's safe to keep the original code here ...

    async def get_trending(
        self, region_code: str = "US", category_id: str = "24",
        limit: int = 25, min_views: int = 0, exclude_reposts: bool = True,
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            return []
        # ... (rest of the get_trending method logic is unchanged)
        # ... it's safe to keep the original code here ...
    
    # ==========================================================
    # --- REFACTORED & NEW METHODS START HERE ---
    # ==========================================================

    def _persist_mention(self, db: Session, creator_handle: str, source_handle: str, video_url: str) -> None:
        """Helper function to persist a single creator mention to the database."""
        stmt = select(Creator).where(Creator.handle == creator_handle)
        creator = db.execute(stmt).scalar_one_or_none()
        
        if not creator:
            creator = Creator(handle=creator_handle)
            db.add(creator)
            db.flush()
            
        mention = CreatorMention(
            creator_id=creator.id,
            source_channel=source_handle,
            source_video_url=video_url
        )
        db.add(mention)

    async def suggest_from_known_channels(
        self,
        db: Session,
        theme_keyword: str,
        channels: list[str] | None = None,
        videos_per_channel: int = 5,
    ) -> dict:
        if not settings.YOUTUBE_API_KEY:
            return {"matched_videos": [], "source_creators_ranked": []}

        channels = channels or KNOWN_RANKING_CHANNELS
        all_matched_videos = []
        handle_counts: dict[str, int] = {}

        print(f"🧠 Investigator: Starting scan of {len(channels)} channels for '{theme_keyword}'...")

        async with httpx.AsyncClient(timeout=20) as client:
            for source_handle in channels:
                try:
                    channel_id = await self._resolve_channel_id(client, source_handle)
                    if not channel_id:
                        continue

                    search_resp = await client.get(SEARCH_URL, params={
                        "part": "snippet", "channelId": channel_id, "q": theme_keyword,
                        "type": "video", "maxResults": videos_per_channel, "order": "date",
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
                        video_url = f"https://www.youtube.com/watch?v={v['id']}"
                        credited_handles = set(CREDIT_HANDLE_PATTERN.findall(desc))

                        if not credited_handles:
                            continue

                        for creator_handle in credited_handles:
                            self._persist_mention(db, creator_handle, source_handle, video_url)
                            handle_counts[creator_handle] = handle_counts.get(creator_handle, 0) + 1

                        all_matched_videos.append({
                            "source_channel": source_handle,
                            "title": v["snippet"]["title"],
                            "url": video_url,
                            "credited_handles": list(credited_handles),
                        })
                except Exception as e:
                    print(f"❌ ERROR checking channel {source_handle}: {e}")
                    db.rollback()
                    continue

        try:
            db.commit()
            print(f"✅ Investigator: Scan complete. Persisted {sum(handle_counts.values())} new mentions.")
        except Exception as e:
            print(f"❌ DATABASE ERROR: Could not commit. Rolling back. Error: {e}")
            db.rollback()

        return {
            "matched_videos": all_matched_videos,
            "source_creators_ranked": sorted(handle_counts.items(), key=lambda x: x[1], reverse=True),
            "channels_checked": channels,
        }

youtube_connector = YouTubeConnector()
