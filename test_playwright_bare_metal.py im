# test_playwright_bare_metal.py
import asyncio
from playwright.async_api import async_playwright

async def main():
    print("🚀 Starting BARE METAL Playwright Test...")
    
    # We will go to a very simple, non-blocking website.
    test_url = "https://www.example.com"
    
    async with async_playwright() as p:
        print("... Launching browser ...")
        try:
            browser = await p.chromium.launch(headless=True)
            print("✅ Browser launched successfully!")
        except Exception as e:
            print(f"❌ FAILED to launch browser. Error: {e}")
            return # Exit if browser fails to launch

        page = await browser.new_page()
        
        try:
            print(f"... Navigating to: {test_url} ...")
            await page.goto(test_url, timeout=30000)
            print("✅ Navigation successful!")

            title = await page.title()
            print(f"   Page title is: '{title}'")
            
            if "Example Domain" in title:
                print("\n✅✅✅ TEST PASSED: Playwright environment is working correctly.")
            else:
                print("\n⚠️ TEST FAILED: Navigation happened but page content is wrong.")

        except Exception as e:
            print(f"\n❌ FAILED during navigation. Error: {e}")
            await page.screenshot(path="bare_metal_error.png")
            print("   A screenshot 'bare_metal_error.png' has been saved.")

        finally:
            print("... Closing browser.")
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
