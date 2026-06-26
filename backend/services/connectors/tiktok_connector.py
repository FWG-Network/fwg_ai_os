# backend/services/connectors/tiktok_connector.py (New name)
import httpx

# The URL you got from deploying the Cloud Function
CLOUD_FUNCTION_URL = "https://your-cloud-function-trigger-url-goes-here"

class TikTokConnector:
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Calls our external Cloud Function agent to perform the TikTok search.
        """
        print(f"📡 TikTok Connector: Outsourcing search for '{query}' to external agent...")
        try:
            async with httpx.AsyncClient(timeout=130) as client:
                response = await client.post(
                    CLOUD_FUNCTION_URL,
                    json={"query": query, "limit": limit}
                )
                response.raise_for_status()
                data = response.json()

                if data.get("status") == "success":
                    print(f"✅ External agent returned {len(data.get('data', []))} videos.")
                    return data.get("data", [])
                else:
                    print(f"❌ External agent failed: {data.get('message')}")
                    return []
        except Exception as e:
            print(f"❌ ERROR: Failed to call external TikTok agent. Error: {e}")
            return []

tiktok_connector = TikTokConnector()
