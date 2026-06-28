"""
TikTok Search Agent — Google Cloud Function
Headless browser scraper via Playwright.
Emits ContentItem-compatible dicts.
"""
import asyncio
import logging
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

log = logging.getLogger("tiktok_agent")
logging.basicConfig(level=logging.INFO)

# ─── Parser (matches ContentItem schema) ──────────────────────────────
def _parse_api_response(api_response: dict) -> list[dict]:
    results = []
    for entry in api_response.get("data", []):
        item   = entry.get("item", {})
        if not item:
            continue
        author = item.get("author", {})
        stats  = item.get("stats",  {})
        vid_id = item.get("id", "")
        handle = author.get("uniqueId", "unknown")

        results.append({
            # ✅ ContentItem compatible
            "id":           vid_id,
            "url":          f"https://www.tiktok.com/@{handle}/video/{vid_id}",
            "title":        item.get("desc", ""),
            "platform":     "tiktok",
            "channel":      author.get("nickname"),
            "views":        stats.get("playCount",   0),
            "likes":        stats.get("diggCount",   0),
            "comments":     stats.get("commentCount",0),
            "shares":       stats.get("shareCount",  0),
            "published_at": item.get("createTime"),
            "source":       "cloud_function",
        })
    return results


# ─── Playwright Scraper ───────────────────────────────────────────────
async def run_playwright_scraper(query: str, limit: int = 10) -> dict:
    ua = UserAgent()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )
        context = await browser.new_context(user_agent=ua.random)
        page    = await context.new_page()

        captured      = asyncio.Event()
        response_data = None

        async def handle_response(response):
            nonlocal response_data
            if (
                "api/search/general/full/" in response.url
                and response.request.method == "GET"
            ):
                try:
                    response_data = await response.json()
                    captured.set()
                    log.info(f"[TikTok] API response captured ✅")
                except Exception as e:
                    log.warning(f"[TikTok] Parse error: {e}")

        page.on("response", handle_response)

        try:
            url = f"https://www.tiktok.com/search/video?q={query}"
            log.info(f"[TikTok] Navigating → {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=45_000)

            # ✅ Fix: timeout=30 (seconds, NOT 30000!)
            await asyncio.wait_for(captured.wait(), timeout=30)

            if response_data:
                results = _parse_api_response(response_data)[:limit]
                log.info(f"[TikTok] ✅ {len(results)} videos found")
                return {"status": "success", "data": results, "count": len(results)}
            else:
                return {"status": "error", "message": "API response not captured", "data": []}

        except asyncio.TimeoutError:
            log.error("[TikTok] ❌ Timeout — TikTok API not captured in 30s")
            return {"status": "timeout", "message": "TikTok API not captured", "data": []}

        except Exception as e:
            log.error(f"[TikTok] ❌ Error: {e}")
            return {"status": "error", "message": str(e), "data": []}

        finally:
            await browser.close()


# ─── Cloud Function Entry Point ───────────────────────────────────────
try:
    from functions_framework import http

    @http
    def tiktok_search_agent(request):
        """HTTP-triggered Cloud Function."""
        body  = request.get_json(silent=True) or {}
        query = body.get("query", "viral video")
        limit = int(body.get("limit", 10))
        log.info(f"[TikTok CF] query='{query}' limit={limit}")
        return asyncio.run(run_playwright_scraper(query, limit))

except ImportError:
    # ✅ Local dev — run directly
    async def _local_test():
        result = await run_playwright_scraper("AI trends", limit=5)
        print(result)

    if __name__ == "__main__":
        asyncio.run(_local_test())
