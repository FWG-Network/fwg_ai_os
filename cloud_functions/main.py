# cloud_functions/main.py
import asyncio
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

# This decorator is from Google Cloud Functions library
from functions_framework import http

# The parser function can be kept the same
def _parse_api_response(api_response: dict) -> list[dict]:
    # ... (Copy the exact same _parse_api_response function from tiktok_agent.py) ...
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
            "id": item.get("id"), "url": video_url, "title": item.get("desc", ""),
            "platform": "tiktok", "channel": author.get("nickname"),
            "views": stats.get("playCount", 0), "likes": stats.get("diggCount", 0),
            "comments": stats.get("commentCount", 0), "shares": stats.get("shareCount", 0),
            "published_at": item.get("createTime"), 
        })
    return results

# This is the main entry point for the Cloud Function
@http
def tiktok_search_agent(request):
    """
    An HTTP-triggered Cloud Function that runs a headless browser
    to scrape TikTok search results.
    """
    request_json = request.get_json(silent=True)
    query = request_json.get('query', 'viral video')
    limit = int(request_json.get('limit', 10))

    # We need to run our async playwright code within a sync function
    # So we create a new event loop
    return asyncio.run(run_playwright_scraper(query, limit))

async def run_playwright_scraper(query: str, limit: int) -> dict:
    """The core async scraping logic."""
    ua = UserAgent()
    async with async_playwright() as p:
        # Important: Specify browser arguments for Cloud Functions environment
        browser_args = ['--disable-dev-shm-usage', '--no-sandbox']
        browser = await p.chromium.launch(headless=True, args=browser_args)
        context = await browser.new_context(user_agent=ua.random)
        page = await context.new_page()

        api_response_captured = asyncio.Event()
        api_response_data = None

        async def handle_response(response):
            nonlocal api_response_data
            if "api/search/general/full/" in response.url and response.request.method == "GET":
                try:
                    api_response_data = await response.json()
                    api_response_captured.set()
                except Exception:
                    pass
        
        page.on("response", handle_response)
        
        try:
            search_url = f"https://www.tiktok.com/search/video?q={query}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
            await asyncio.wait_for(api_response_captured.wait(), timeout=30000)
            
            if api_response_data:
                results = _parse_api_response(api_response_data)
                return {"status": "success", "data": results[:limit]}
            else:
                return {"status": "error", "message": "API response not captured"}

        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            await browser.close()
