# test_tiktok_agent.py
import asyncio
import json

# Import the agent we want to test
from backend.services.connectors.tiktok_agent import tiktok_agent

async def main():
    """
    A simple async function to run our TikTok agent and see the results.
    """
    print("🚀 Starting TikTok Agent Test Drive...")
    
    # Let's search for a keyword
    # You can change this keyword to anything you want to test
    search_keyword = "khmer traditional dance"
    
    results = await tiktok_agent.search(query=search_keyword, limit=5)
    
    if results:
        print(f"\n✅ SUCCESS! Found {len(results)} videos for '{search_keyword}':")
        # Pretty-print the JSON result so it's easy to read
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("\n⚠️ Agent finished but found 0 videos.")
        print("   This could be normal (no results for keyword) or an error.")
        print("   Check for any '❌ ERROR' messages above or screenshot files.")

if __name__ == "__main__":
    # This is how we run an async function from a regular Python script
    asyncio.run(main())
