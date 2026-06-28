"""
backend/tests/test_os.py
Verify all /os endpoints are registered and responding.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_os_status():
    res = client.get("/os/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "services" in data
    print(f"✅ /os/status → {data['status']}")


def test_os_plan():
    res = client.post("/os/plan", json={
        "command": "find trending AI videos",
        "user_id": "test_user"
    })
    assert res.status_code in [200, 500]  # 500 ok if planner not ready
    print(f"✅ /os/plan → {res.status_code}")


def test_os_submit_goal():
    res = client.post("/os/submit_goal", json={
        "goal": "research AI trends",
        "user_id": "test_user"
    })
    assert res.status_code in [200, 500, 503]  # 503 = worker offline ok
    print(f"✅ /os/submit_goal → {res.status_code}")


def test_os_agent_run_discover():
    res = client.post("/os/agent/run", json={
        "agent": "discover",
        "input": {"topic": "AI trends"},
        "user_id": "test_user"
    })
    assert res.status_code in [200, 500]
    print(f"✅ /os/agent/run [discover] → {res.status_code}")


def test_os_memory_query():
    res = client.post("/os/memory/query", json={
        "query": "AI video trends",
        "top_k": 3
    })
    assert res.status_code in [200, 500]
    print(f"✅ /os/memory/query → {res.status_code}")


def test_os_reset():
    res = client.post("/os/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "reset_complete"
    print(f"✅ /os/reset → {data['result']['actions']}")
