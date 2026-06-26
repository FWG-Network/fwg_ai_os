# backend/services/connectors/tiktok_agent.py
import asyncio
import json
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

class TikTokHeadlessAgent:
    
    def __init__(self):
        self.ua = UserAgent()

    def _parse_api_response(self, api_response: dict) -> list[dict]:
        """
        🚀 TRANSPLANT from HasData's extract_useful_data function.
        This part is responsible for transforming the raw TikTok API JSON
        into our clean, internal data format.
        """
        results = []
        data_list = api_response.get("data", [])

        for entry in data_list:
            item = entry.get("item", {})
            if not item: continue

            video = item.get("video", {})
            author = item.get("author", {})
            stats = item.get("stats", {})
            
            video_url = f"https://www.tiktok.com/@{author.get('uniqueId')}/video/{item.get('id')}"

            results.append({
                "id": item.get("id"),
                "url": video_url,
                "title": item.get("desc", ""),
                "platform": "tiktok",
                "channel": author.get("nickname"),
                "views": stats.get("playCount", 0),
                "likes": stats.get("diggCount", 0),
                "comments": stats.get("commentCount", 0),
                "shares": stats.get("shareCount", 0),
                # Convert timestamp to ISO format if needed, or keep as is
                "published_at": item.get("createTime"), 
            })
        return results

    async def search(self, query: str, limit: int = 20) -> list[dict]:
        """
        Uses a headless browser to intercept TikTok's internal search API.
        This is a robust method inspired by the HasData repository.
        """
        print(f"🤖 TikTok Agent: Initializing search for '{query}'...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=self.ua.random)
            page = await context.new_page()

            # This event will signal us when the API response is captured
            api_response_captured = asyncio.Event()
            api_response_data = None

            # In backend/services/connectors/tiktok_agent.py
# Inside the search method...

async def handle_response(response):
    nonlocal api_response_data
    # 🚀 DIAGNOSTIC UPGRADE: Log ALL responses to see what's happening
    print(f"   [Network Log] Intercepted: {response.request.method} {response.url[:100]}...")
    
    if "api/search/general/full/" in response.url and response.request.method == "GET":
        try:
            print(f"✅ SUCCESS: Intercepted the correct TikTok API Response!")
            api_response_data = await response.json()
            api_response_captured.set()
        except Exception as e:
            print(f"⚠️ Could not parse the correct API response: {e}")

page.on("response", handle_response)

try:
    search_url = f"https://www.tiktok.com/search/video?q={query}"
    print(f"... Navigating to {search_url}")
    # 🚀 DIAGNOSTIC UPGRADE: Increase navigation timeout
    await page.goto(search_url, wait_until="networkidle", timeout=60000)

    print("... Page navigation complete. Waiting for API response (up to 45s)...")
    # 🚀 DIAGNOSTIC UPGRADE: Increase wait timeout
    await asyncio.wait_for(api_response_captured.wait(), timeout=45000)
    
    # (inside the try block)
            search_url = f"https://www.tiktok.com/search/video?q={query}"
            print(f"... Navigating to {search_url}")
            await page.goto(search_url, wait_until="networkidle", timeout=60000)

            print("... Waiting for API response (up to 45s)...") # <--- CORRECT (aligned with lines above)
            await asyncio.wait_for(api_response_captured.wait(), timeout=45000)
                
                if api_response_data:
                    parsed_results = self._parse_api_response(api_response_data)
                    print(f"✅ TikTok Agent: Successfully extracted {len(parsed_results)} videos.")
                    return parsed_results[:limit]
                else:
                    print("⚠️ TikTok Agent: Page loaded but API response was not captured.")
                    return []

            except asyncio.TimeoutError:
                print(f"❌ ERROR: Timed out waiting for TikTok's search API to respond.")
                await page.screenshot(path=f"debug_timeout_{query}.png")
                return []
            except Exception as e:
                print(f"❌ ERROR: TikTok Headless Agent failed. Error: {e}")
                await page.screenshot(path=f"debug_error_{query}.png")
                return []
            finally:
                await browser.close()
        
        return []

tiktok_agent = TikTokHeadlessAgent()
