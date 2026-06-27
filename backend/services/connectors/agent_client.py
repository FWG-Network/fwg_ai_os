# backend/services/connectors/agent_client.py
import asyncio
import httpx
from dotenv import load_dotenv
import os

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
AGENT_URL = os.getenv("AGENT_URL", "https://sereyfwg-agent.hf.space")
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}


async def health_check() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{AGENT_URL}/health", headers=HEADERS)
        response.raise_for_status()
        return response.json()


async def call_agent(endpoint: str, data: dict | None = None, max_retries: int = 3) -> dict:
    data = data or {}  # ★ fix mutable default
    last_exc = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(f"{AGENT_URL}{endpoint}", json=data, headers=HEADERS)
                response.raise_for_status()
                return response.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exc = e
            if attempt < max_retries - 1:
                wait = 30 if attempt == 0 else 60
                print(f"⚠️ HF Space may be sleeping. Waiting {wait}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
            else:
                print("❌ Agent unreachable after all retries.")
                raise last_exc
        except httpx.HTTPStatusError as e:
            print(f"❌ Agent error: {e.response.status_code}")
            raise
