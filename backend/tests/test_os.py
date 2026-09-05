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


def test_os_submit_goal_fallback_strict(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from backend.api.endpoints import os as os_endpoint

    async def fail_worker(task):
        raise HTTPException(
            status_code=503,
            detail="Worker unavailable after 3 retries",
        )

    class FakeAutonomousLoop:
        async def run(self, goal_description, user_id, db):
            assert goal_description == "research AI trends"
            assert user_id == "test_user"
            assert db is not None
            return SimpleNamespace(id=123, status="completed")

    monkeypatch.setattr(
        os_endpoint.worker_client,
        "submit_task",
        fail_worker,
    )
    import backend.aios.autonomous_loop as autonomous_loop_module

    monkeypatch.setattr(
        autonomous_loop_module,
        "autonomous_loop_service",
        FakeAutonomousLoop(),
    )

    res = client.post("/os/submit_goal", json={
        "goal": "research AI trends",
        "user_id": "test_user",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == "123"
    assert data["status"] == "completed"


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


def test_os_agent_run_discover_strict(monkeypatch):
    from types import SimpleNamespace
    from backend.api.endpoints import os as os_endpoint

    class FakeDiscovery:
        async def discover(self, topic):
            assert topic == "AI trends"
            return [{"title": "clip-1"}]

    class FakeRanking:
        def rank(self, candidates, user_id=None):
            assert candidates == [{"title": "clip-1"}]
            assert user_id == "test_user"
            return [{"title": "clip-1", "score": 0.99}]

    monkeypatch.setattr(os_endpoint, "_get_discovery", lambda: FakeDiscovery())
    monkeypatch.setattr(os_endpoint, "_get_ranking", lambda: FakeRanking())

    res = client.post("/os/agent/run", json={
        "agent": "discover",
        "input": {"topic": "AI trends"},
        "user_id": "test_user",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["agent"] == "discover+rank"
    assert data["result"]["total"] == 1
    assert data["result"]["ranked_content"] == [
        {"title": "clip-1", "score": 0.99}
    ]


def test_os_agent_run_trend(monkeypatch):
    from types import SimpleNamespace
    from backend.api.endpoints import os as os_endpoint

    class FakePlanner:
        def create_plan(self, command, user_id):
            assert command == "trend AI"
            assert user_id == "test_user"
            return object()

    tasks = [
        SimpleNamespace(tool_name="trend_scanner", description="scan AI trends")
    ]

    monkeypatch.setattr(os_endpoint, "_get_planner", lambda: FakePlanner())
    monkeypatch.setattr(os_endpoint, "_flatten_tasks", lambda staged: tasks)

    res = client.post("/os/agent/run", json={
        "agent": "trend",
        "input": {"keywords": ["AI"]},
        "user_id": "test_user",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["agent"] == "trend_scanner"
    assert data["result"] == [
        {"tool": "trend_scanner", "desc": "scan AI trends"}
    ]


def test_os_agent_run_llm(monkeypatch):
    from types import SimpleNamespace
    from backend.api.endpoints import os as os_endpoint

    class FakePlanner:
        def create_plan(self, command, user_id):
            assert command == "research AI video trends"
            assert user_id == "test_user"
            return object()

    tasks = [
        SimpleNamespace(tool_name="llm", description="analyze AI video trends")
    ]
    monkeypatch.setattr(os_endpoint, "_get_planner", lambda: FakePlanner())
    monkeypatch.setattr(os_endpoint, "_flatten_tasks", lambda staged: tasks)

    res = client.post("/os/agent/run", json={
        "agent": "llm",
        "input": {"prompt": "research AI video trends"},
        "user_id": "test_user",
    })

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["agent"] == "llm"
    assert data["result"] == [
        {"tool": "llm", "desc": "analyze AI video trends"}
    ]


def test_os_task_status_falls_back_to_goal_db(monkeypatch):
    from fastapi import HTTPException
    from backend.api.endpoints import os as os_endpoint
    from backend.models.db import Goal as GoalModel, SessionLocal

    async def worker_unavailable(_task_id: str):
        raise HTTPException(
            status_code=503,
            detail="Worker unavailable",
        )

    monkeypatch.setattr(
        os_endpoint.worker_client,
        "get_task_status",
        worker_unavailable,
    )

    db = SessionLocal()
    goal = GoalModel(
        user_id="test-task-status",
        description="strict task status fallback",
        status="completed",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    try:
        response = client.get(f"/os/task/status/{goal_id}")

        assert response.status_code == 200
        assert response.json() == {
            "task_id": str(goal_id),
            "status": "completed",
            "result": None,
            "error": None,
        }
    finally:
        cleanup = SessionLocal()
        persisted = cleanup.get(GoalModel, goal_id)
        if persisted is not None:
            cleanup.delete(persisted)
        cleanup.commit()
        cleanup.close()


def test_os_execute_async_falls_back_to_local_aios(monkeypatch):
    from fastapi import HTTPException
    from backend.api.endpoints import os as os_endpoint

    async def worker_unavailable(_task):
        raise HTTPException(
            status_code=503,
            detail="Worker unavailable",
        )

    class FakeGoal:
        id = 990001
        status = "completed"

    async def fake_run(*, goal_description, user_id, db):
        assert goal_description == "fallback execute test"
        assert user_id == "test-user"
        assert db is not None
        return FakeGoal()

    monkeypatch.setattr(
        os_endpoint.worker_client,
        "submit_task",
        worker_unavailable,
    )

    from backend.aios.autonomous_loop import autonomous_loop_service

    monkeypatch.setattr(
        autonomous_loop_service,
        "run",
        fake_run,
    )

    response = client.post(
        "/os/execute",
        json={
            "command": "fallback execute test",
            "user_id": "test-user",
            "async_mode": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["task_id"] == "990001"


def test_os_memory_query_strict_success(monkeypatch):
    from backend.lim.vector_memory import vector_memory_service

    calls = {}

    def fake_search(query, top_k, collection):
        calls["args"] = (query, top_k, collection)
        return [
            {
                "id": "mem-1",
                "score": 0.9876,
                "text": "AI video trend",
                "metadata": {"source": "test"},
            }
        ]

    monkeypatch.setattr(
        vector_memory_service,
        "search",
        fake_search,
    )

    res = client.post(
        "/os/memory/query",
        json={
            "query": "AI video trends",
            "top_k": 3,
            "collection": "fwg_test",
        },
    )

    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "completed"
    assert data["agent"] == "vector_memory"
    assert data["result"]["query"] == "AI video trends"
    assert data["result"]["top_k"] == 3
    assert data["result"]["results"] == [
        {
            "id": "mem-1",
            "score": 0.9876,
            "text": "AI video trend",
            "metadata": {"source": "test"},
        }
    ]
    assert calls["args"] == (
        "AI video trends",
        3,
        "fwg_test",
    )


def test_os_memory_query_rejects_invalid_top_k():
    for top_k in (0, 21):
        res = client.post(
            "/os/memory/query",
            json={
                "query": "AI video trends",
                "top_k": top_k,
            },
        )

        assert res.status_code == 422


def test_os_memory_query_propagates_service_failure_as_500(monkeypatch):
    from backend.lim.vector_memory import vector_memory_service

    def failing_search(query, top_k, collection):
        raise RuntimeError("memory backend failure")

    monkeypatch.setattr(
        vector_memory_service,
        "search",
        failing_search,
    )

    res = client.post(
        "/os/memory/query",
        json={
            "query": "AI video trends",
            "top_k": 3,
        },
    )

    assert res.status_code == 500
    assert res.json()["detail"] == "memory backend failure"


def test_os_memory_query_uses_existing_vector_memory_singleton(monkeypatch):
    from backend.lim.vector_memory import vector_memory_service

    sentinel = [
        {
            "id": "singleton-1",
            "score": 1.0,
            "text": "singleton",
            "metadata": {},
        }
    ]

    monkeypatch.setattr(
        vector_memory_service,
        "search",
        lambda query, top_k, collection: sentinel,
    )

    res = client.post(
        "/os/memory/query",
        json={
            "query": "singleton check",
            "top_k": 1,
        },
    )

    assert res.status_code == 200
    assert res.json()["result"]["results"] == sentinel


def test_os_reset_flushes_discovery_cache_db2_and_resets_singletons(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    class FakeRedis:
        def __init__(self):
            self.flushdb_calls = 0

        def flushdb(self):
            self.flushdb_calls += 1

    fake_redis = FakeRedis()
    captured = {}

    class FakeRedisLib:
        @staticmethod
        def from_url(url, **kwargs):
            captured["url"] = url
            captured["kwargs"] = kwargs
            return fake_redis

    monkeypatch.setitem(__import__("sys").modules, "redis", FakeRedisLib)

    sentinel_planner = object()
    sentinel_discovery = object()
    sentinel_ranking = object()

    os_endpoint._task_planner = sentinel_planner
    os_endpoint._discovery_engine = sentinel_discovery
    os_endpoint._ranking_engine = sentinel_ranking

    res = client.post("/os/reset")

    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "reset_complete"
    assert "discovery_cache_cleared (db=2)" in data["result"]["actions"]
    assert "service_singletons_reset" in data["result"]["actions"]
    assert fake_redis.flushdb_calls == 1
    assert captured["kwargs"]["db"] == 2
    assert captured["kwargs"]["socket_timeout"] == 2
    assert os_endpoint._task_planner is None
    assert os_endpoint._discovery_engine is None
    assert os_endpoint._ranking_engine is None


def test_os_reset_reports_redis_unavailable_and_still_resets_singletons(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    class FakeRedisLib:
        @staticmethod
        def from_url(url, **kwargs):
            raise RuntimeError("redis unavailable")

    monkeypatch.setitem(__import__("sys").modules, "redis", FakeRedisLib)

    os_endpoint._task_planner = object()
    os_endpoint._discovery_engine = object()
    os_endpoint._ranking_engine = object()

    res = client.post("/os/reset")

    assert res.status_code == 200

    data = res.json()
    assert data["status"] == "reset_complete"
    assert "redis_unavailable_skipped" in data["result"]["actions"]
    assert "service_singletons_reset" in data["result"]["actions"]
    assert os_endpoint._task_planner is None
    assert os_endpoint._discovery_engine is None
    assert os_endpoint._ranking_engine is None
