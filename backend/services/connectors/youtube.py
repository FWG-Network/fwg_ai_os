# backend/services/connectors/youtube.py
import httpx
from datetime import datetime, timedelta
from backend.core.config import settings

YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"

class YouTubeConnector:
    async def search(
        self, 
        query: str, 
        limit: int = 10,
        days_ago_start: int = 7, # Search from 7 days ago
        days_ago_end: int = 0    # To now
    ) -> list[dict]:
        if not settings.YOUTUBE_API_KEY:
            print("⚠️ WARNING: YOUTUBE_API_KEY not set. Returning mock YouTube data.")
            # Keep mock data for when key is not present
            return [{"id": f"yt_mock_{query.replace(' ','_')}", "title": f"Mock YouTube: {query}", "platform": "youtube", "tags": [query.split(' ')[-1]], "published_at": datetime.utcnow().isoformat()}]

        # --- REAL API LOGIC STARTS HERE ---
        
        # Calculate date range
        start_time = datetime.utcnow() - timedelta(days=days_ago_start)
        end_time = datetime.utcnow() - timedelta(days=days_ago_end)
        
        params = {
            "part": "snippet",
            "q": query,
            "key": settings.YOUTUBE_API_KEY,
            "maxResults": limit,
            "type": "video",
            "order": "viewCount", # Or relevance, date, etc.
            "publishedAfter": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "publishedBefore": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        }
        
        async with httpx.AsyncClient() as client:
            try:
                print(f"📡 YouTubeConnector: Searching for '{query}'...")
                response = await client.get(YOUTUBE_API_URL, params=params)
                response.raise_for_status() # Raise exception for bad responses (4xx or 5xx)
                data = response.json()
                
                # Transform the API response to our internal format
                return [
                    {
                        "id": item["id"]["videoId"],
                        "title": item["snippet"]["title"],
                        "platform": "youtube",
                        "tags": item["snippet"].get("tags", []),
                        "published_at": item["snippet"]["publishedAt"] # Store exact timestamp
                    }
                    for item in data.get("items", [])
                ]
            except httpx.HTTPStatusError as e:
                print(f"❌ ERROR: Failed to fetch from YouTube API. Status: {e.response.status_code}, Response: {e.response.text}")
                return []
            except Exception as e:
                print(f"❌ ERROR: An unexpected error occurred: {e}")
                return []

youtube_connector = YouTubeConnector()
