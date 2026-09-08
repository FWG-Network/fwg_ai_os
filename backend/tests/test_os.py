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
        "user_id": "test_user",
        "idempotency_key": "test-os-submit-goal",
    })
    assert res.status_code in [200, 500, 503]  # 503 = worker offline ok
    print(f"✅ /os/submit_goal → {res.status_code}")


def test_os_submit_goal_local_authority(monkeypatch):
    from types import SimpleNamespace
    from backend.models.db import AIOSIdempotencyRecord, Goal, SessionLocal, Task

    class FakeAutonomousLoop:
        async def run(self, goal_description, user_id, db):
            assert goal_description == "research AI trends"
            assert user_id == "test_user"
            assert db is not None
            goal = Goal(
                description=goal_description,
                user_id=user_id,
                status="completed",
            )
            db.add(goal)
            db.commit()
            db.refresh(goal)
            return goal

    import backend.aios.autonomous_loop as autonomous_loop_module

    monkeypatch.setattr(
        autonomous_loop_module,
        "autonomous_loop_service",
        FakeAutonomousLoop(),
    )

    try:
        res = client.post("/os/submit_goal", json={
            "goal": "research AI trends",
            "user_id": "test_user",
            "idempotency_key": "test-os-submit-goal-local-authority",
        })

        assert res.status_code == 200
        data = res.json()
        goal_id = int(data["task_id"])
        assert data["status"] == "completed"
    finally:
        db = SessionLocal()
        db.query(AIOSIdempotencyRecord).filter(
            AIOSIdempotencyRecord.goal_id == goal_id
        ).delete(synchronize_session=False)
        goal = db.get(Goal, goal_id)
        if goal is not None:
            db.query(Task).filter(Task.goal_id == goal_id).delete(
                synchronize_session=False
            )
            db.delete(goal)
        db.commit()
        db.close()


def test_os_submit_goal_local_execution_contract(monkeypatch):
    from backend.api.endpoints import os as os_endpoint
    from backend.aios.executor import executor_service
    from backend.aios.reflection import reflection_service
    from backend.aios.task_planner import task_planner_service
    from backend.models.db import (
        AIOSIdempotencyRecord,
        Goal as GoalModel,
        SessionLocal,
        Task as TaskModel,
    )

    calls = {
        "planner": 0,
        "executor": 0,
        "reflection": 0,
    }

    def local_plan(goal_description, goal_id):
        calls["planner"] += 1
        assert goal_description == "local execution contract"
        return [[
            TaskModel(
                description="Run deterministic local ranking",
                goal_id=goal_id,
                tool_name="ranking_engine",
                tool_params={"candidates": []},
            )
        ]]

    original_execute_task = executor_service.execute_task
    original_reflection = reflection_service.evaluate

    async def execute_task_spy(
        task,
        db,
        user_id="aios_system",
        resolved_inputs=None,
    ):
        calls["executor"] += 1
        return await original_execute_task(
            task,
            db,
            user_id,
            resolved_inputs,
        )

    def reflection_spy(goal):
        calls["reflection"] += 1
        return original_reflection(goal)

    monkeypatch.setattr(task_planner_service, "create_plan", local_plan)
    monkeypatch.setattr(executor_service, "execute_task", execute_task_spy)
    monkeypatch.setattr(reflection_service, "evaluate", reflection_spy)

    response = client.post(
        "/os/submit_goal",
        json={
            "goal": "local execution contract",
            "user_id": "test-user",
            "idempotency_key": "test-os-local-execution",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert calls == {
        "planner": 1,
        "executor": 1,
        "reflection": 1,
    }

    goal_id = int(data["task_id"])
    db = SessionLocal()
    try:
        goal = db.get(GoalModel, goal_id)
        assert goal is not None
        assert goal.status == "completed"
        assert len(goal.tasks) == 1
        assert goal.tasks[0].status == "completed"
        assert goal.tasks[0].result == {
            "tool": "ranking_engine",
            "ranked": [],
        }
    finally:
        goal = db.get(GoalModel, goal_id)
        if goal is not None:
            db.query(AIOSIdempotencyRecord).filter(
                AIOSIdempotencyRecord.goal_id == goal_id
            ).delete(synchronize_session=False)
            for task in goal.tasks:
                db.delete(task)
            db.delete(goal)
        db.commit()
        db.close()


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



def test_os_agent_run_discover_real_pipeline():
    """Real runtime verification: Discovery -> Intelligence -> Evaluation -> Ranking."""
    res = client.post(
        "/os/agent/run",
        json={
            "agent": "discover",
            "input": {"topic": "AI video trends"},
            "user_id": "test_user",
        },
    )

    assert res.status_code == 200

    data = res.json()

    assert data["status"] == "completed"
    assert data["agent"] == "discover+rank"
    assert isinstance(data["result"]["ranked_content"], list)
    assert data["result"]["total"] == len(
        data["result"]["ranked_content"]
    )

    ranked = data["result"]["ranked_content"]

    # Real discovery is required to produce at least one candidate.
    assert ranked, "Real discovery returned no candidates"

    first = ranked[0]

    # Intelligence + Evaluation must survive into final ranking output.
    assert "intelligence" in first
    assert "evaluation" in first
    assert "_score_debug" in first

    intelligence = first["intelligence"]
    evaluation = first["evaluation"]

    assert "editorial_relevance" in intelligence
    assert "viral_potential" in intelligence
    assert "content_quality" in intelligence
    assert "evidence_confidence" in intelligence

    assert evaluation["decision"] in {
        "accept",
        "reject",
    }

    # Ranking must have consumed the intelligence-derived semantic score.
    assert "semantic" in first["_score_debug"]

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


def test_os_task_status_uses_goal_db_authority():
    from backend.models.db import Goal as GoalModel, SessionLocal

    db = SessionLocal()
    goal = GoalModel(
        user_id="test-task-status",
        description="strict local task status",
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
            "idempotency_record_id": None,
        }
    finally:
        cleanup = SessionLocal()
        persisted = cleanup.get(GoalModel, goal_id)
        if persisted is not None:
            cleanup.delete(persisted)
        cleanup.commit()
        cleanup.close()


def test_os_task_status_returns_local_state_when_worker_would_disagree():
    from backend.models.db import Goal as GoalModel, SessionLocal

    db = SessionLocal()
    goal = GoalModel(
        user_id="test-task-status-authority",
        description="local status authority",
        status="failed",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    db.close()

    try:
        response = client.get(f"/os/task/status/{goal_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
    finally:
        cleanup = SessionLocal()
        persisted = cleanup.get(GoalModel, goal_id)
        if persisted is not None:
            cleanup.delete(persisted)
        cleanup.commit()
        cleanup.close()


def test_os_task_status_returns_truthful_not_found():
    response = client.get("/os/task/status/999999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Local task not found: 999999999"


def test_os_execute_async_uses_local_aios(monkeypatch):
    from backend.models.db import AIOSIdempotencyRecord, Goal, SessionLocal, Task

    async def fake_run(*, goal_description, user_id, db):
        assert goal_description == "local execute test"
        assert user_id == "test-user"
        assert db is not None
        goal = Goal(
            description=goal_description,
            user_id=user_id,
            status="completed",
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    from backend.aios.autonomous_loop import autonomous_loop_service

    monkeypatch.setattr(
        autonomous_loop_service,
        "run",
        fake_run,
    )

    goal_id = None
    try:
        response = client.post(
            "/os/execute",
            json={
                "command": "local execute test",
                "user_id": "test-user",
                "async_mode": True,
                "idempotency_key": "test-os-local-execute",
            },
        )

        assert response.status_code == 200
        data = response.json()
        goal_id = int(data["task_id"])
        assert data["status"] == "completed"
    finally:
        if goal_id is not None:
            db = SessionLocal()
            db.query(AIOSIdempotencyRecord).filter(
                AIOSIdempotencyRecord.goal_id == goal_id
            ).delete(synchronize_session=False)
            goal = db.get(Goal, goal_id)
            if goal is not None:
                db.query(Task).filter(Task.goal_id == goal_id).delete(
                    synchronize_session=False
                )
                db.delete(goal)
            db.commit()
            db.close()


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


def test_os_status_all_services_online(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    monkeypatch.setattr(os_endpoint, "_ping_qdrant", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_db", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_redis", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_worker", lambda: "online")

    res = client.get("/os/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "operational"
    assert data["services"]["qdrant"] == "online"
    assert data["services"]["database"] == "online"
    assert data["services"]["redis"] == "online"
    assert data["services"]["celery_worker"] == "online"


def test_os_status_optional_service_offline_is_degraded(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    monkeypatch.setattr(os_endpoint, "_ping_qdrant", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_db", lambda: "online")
    monkeypatch.setattr(
        os_endpoint,
        "_ping_redis",
        lambda: "offline (personalization degraded)",
    )
    monkeypatch.setattr(
        os_endpoint,
        "_ping_worker",
        lambda: "offline (async tasks unavailable)",
    )

    res = client.get("/os/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "degraded"
    assert "offline" in data["services"]["redis"]
    assert "offline" in data["services"]["celery_worker"]


def test_os_status_degraded_worker_is_degraded(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    monkeypatch.setattr(os_endpoint, "_ping_qdrant", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_db", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_redis", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_worker", lambda: "degraded")

    res = client.get("/os/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "degraded"
    assert data["services"]["celery_worker"] == "degraded"


def test_os_status_critical_service_offline_is_critical(monkeypatch):
    from backend.api.endpoints import os as os_endpoint

    monkeypatch.setattr(os_endpoint, "_ping_qdrant", lambda: "offline")
    monkeypatch.setattr(os_endpoint, "_ping_db", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_redis", lambda: "online")
    monkeypatch.setattr(os_endpoint, "_ping_worker", lambda: "online")

    res = client.get("/os/status")

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "critical"
    assert data["services"]["qdrant"] == "offline"
    assert data["services"]["database"] == "online"


def test_os_plan_strict(monkeypatch):
    from types import SimpleNamespace
    from backend.api.endpoints import os as os_endpoint

    calls = {}

    class FakePlanner:
        def create_plan(self, command, user_id):
            calls["command"] = command
            calls["user_id"] = user_id
            return [
                [
                    SimpleNamespace(
                        description="Search trending AI videos",
                        tool_name="youtube_search",
                    ),
                    SimpleNamespace(
                        description="Rank discovered videos",
                        tool_name="ranking_engine",
                    ),
                ],
                [
                    SimpleNamespace(
                        description="Prepare final shortlist",
                        tool_name="content_selector",
                    ),
                ],
            ]

    monkeypatch.setattr(
        os_endpoint,
        "_get_planner",
        lambda: FakePlanner(),
    )

    res = client.post(
        "/os/plan",
        json={
            "command": "find trending AI videos",
            "user_id": "test_user",
        },
    )

    assert res.status_code == 200

    data = res.json()

    assert data["status"] == "planned"
    assert data["plan"] == [
        "Search trending AI videos",
        "Rank discovered videos",
        "Prepare final shortlist",
    ]
    assert data["agent"] == "youtube_search"

    assert calls["command"] == "find trending AI videos"
    assert calls["user_id"] == "test_user"
