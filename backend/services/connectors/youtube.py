# backend/services/connectors/youtube.py

import re
import httpx
from datetime import datetime, timedelta

# 🚀 UPGRADE V3: Import necessary database components
from sqlalchemy.orm import Session
from backend.models.db import Creator, CreatorMention
# ===============================================

from backend.core.config import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
CHANNELS_URL = "https://www.googleapis.com/youtube/v3/channels"

REPOST_KEYWORDS = ["compilation", "reaction to", "react to", "reupload", "best of"]
CREDIT_HANDLE_PATTERN = re.compile(r'@[\w.-]+') # Improved regex to include dots and hyphens

KNOWN_RANKING_CHANNELS = ["PolarRanks", "oogway_ranks", "mrpurifiedwater", "Data Drip"]

class YouTubeConnector:

    def __init__(self):
        self._channel_id_cache: dict[str, str | None] = {}

    # ... (The following methods are unchanged as they are not part of this upgrade)
    # _resolve_channel_id
    # _build_results
    # search
    # get_trending
    # ... I am omitting them here for brevity, but they should remain in your file ...

    # =================================================================================
    # 🚀 UPGRADE V3: The Investigator now writes its findings to memory
    # =================================================================================
    async def suggest_from_known_channels(
        self,
        db: Session,  # ★ ADDED: Database session is now a required parameter
        theme_keyword: str,
        channels: list[str] | None = None,
        videos_per_channel: int = 5,
    ) -> dict:
        """
        Searches videos from known curator channels, extracts credited creator handles,
        and PERSISTS these mentions to the database for trend analysis.
        """
        if not settings.YOUTUBE_API_KEY:
            return {"matched_videos": [], "source_creators_ranked": []}

        channels = channels or KNOWN_RANKING_CHANNELS
        all_matched_videos = []
        handle_counts: dict[str, int] = {}

        print(f"🧠 Investigator: Starting scan of {len(channels)} known channels for '{theme_keyword}'...")

        async with httpx.AsyncClient(timeout=20) as client:
            for handle in channels:
                try:
                    channel_id = await self._resolve_channel_id(client, handle)
                    if not channel_id:
                        print(f"⚠️ Channel handle not found, skipping: {handle}")
                        continue

                    # Search for videos within this specific channel
                    search_resp = await client.get(SEARCH_URL, params={
                        "part": "snippet", "channelId": channel_id, "q": theme_keyword,
                        "type": "video", "maxResults": videos_per_channel, "order": "date",
                        "key": settings.YOUTUBE_API_KEY,
                    })
                    search_resp.raise_for_status()
                    videos = search_resp.json().get("items", [])
                    if not videos:
                        continue
                    
                    # Get full details (including description) for found videos
                    video_ids = ",".join(v["id"]["videoId"] for v in videos)
                    detail_resp = await client.get(VIDEOS_URL, params={
                        "part": "snippet", "id": video_ids, "key": settings.YOUTUBE_API_KEY,
                    })
                    detail_resp.raise_for_status()

                    for v in detail_resp.json().get("items", []):
                        desc = v["snippet"].get("description", "")
                        video_url = f"https://www.youtube.com/watch?v={v['id']}"
                        
                        # Find all unique @handles in the description
                        credited_handles = set(CREDIT_HANDLE_PATTERN.findall(desc))

                        # ★ DATABASE LOGIC: Record each mention in our memory ★
                        for creator_handle in credited_handles:
                            # 1. Find or Create the Creator in our database
                            creator = db.query(Creator).filter(Creator.handle == creator_handle).first()
                            if not creator:
                                creator = Creator(handle=creator_handle)
                                db.add(creator)
                                # We don't commit yet, we do it once at the end.
                                # But we need to flush to get the creator object ready for the relationship.
                                db.flush()
                            
                            # 2. Create the CreatorMention record
                            mention = CreatorMention(
                                creator_id=creator.id,
                                source_channel=handle,
                                source_video_url=video_url
                            )
                            db.add(mention)

                            # Also update the in-memory counter for the immediate response
                            handle_counts[creator_handle] = handle_counts.get(creator_handle, 0) + 1

                        all_matched_videos.append({
                            "source_channel": handle,
                            "title": v["snippet"]["title"],
                            "url": video_url,
                            "credited_handles": list(credited_handles),
                        })

                except Exception as e:
                    print(f"❌ ERROR checking channel {handle}: {e}")
                    # If something goes wrong with one channel, we rollback changes for that channel
                    # and continue to the next one.
                    db.rollback()
                    continue

        try:
            # Commit all the new Creator and CreatorMention records in a single transaction
            db.commit()
            print(f"✅ Investigator: Scan complete. Persisted {sum(handle_counts.values())} new mentions to the database.")
        except Exception as e:
            print(f"❌ DATABASE ERROR: Could not commit mentions. Rolling back. Error: {e}")
            db.rollback()

        return {
            "matched_videos": all_matched_videos,
            "source_creators_ranked": sorted(handle_counts.items(), key=lambda x: x[1], reverse=True),
            "channels_checked": channels,
        }

youtube_connector = YouTubeConnector()
