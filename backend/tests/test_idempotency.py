from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.main import app
from backend.api.endpoints import os as os_endpoint
from backend.models.db import (
    AIOSIdempotencyRecord,
    Goal,
    SessionLocal,
    Task,
)


client = TestClient(app)


def _db():
    return SessionLocal()


def _persist_goal(db, *, goal_description, user_id, status):
    goal = Goal(
        description=goal_description,
        user_id=user_id,
        status=status,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@pytest.fixture(autouse=True)
def clean_idempotency_records():
    db = _db()
    db.query(AIOSIdempotencyRecord).delete()
    user_ids = {
        "idempotency-user",
        "conflict-user",
        "concurrent-endpoint-user",
        "replay-user",
        "execute-user",
        "execute-local-user",
        "reserved-user",
        "reserved-worker-user",
        "reserved-goal-user",
    }
    goal_ids = [
        goal_id
        for (goal_id,) in db.query(Goal.id).filter(Goal.user_id.in_(user_ids)).all()
    ]
    if goal_ids:
        db.query(Task).filter(Task.goal_id.in_(goal_ids)).delete(
            synchronize_session=False
        )
        db.query(Goal).filter(Goal.id.in_(goal_ids)).delete(
            synchronize_session=False
        )
    db.commit()
    db.close()
    yield
    db = _db()
    db.query(AIOSIdempotencyRecord).delete()
    goal_ids = [
        goal_id
        for (goal_id,) in db.query(Goal.id).filter(Goal.user_id.in_(user_ids)).all()
    ]
    if goal_ids:
        db.query(Task).filter(Task.goal_id.in_(goal_ids)).delete(
            synchronize_session=False
        )
        db.query(Goal).filter(Goal.id.in_(goal_ids)).delete(
            synchronize_session=False
        )
    db.commit()
    db.close()


def test_submit_goal_first_request_and_same_key_replay(monkeypatch):
    calls = {"worker": 0, "loop": 0}

    async def unavailable(_request):
        calls["worker"] += 1
        raise HTTPException(status_code=503, detail="offline")

    class FakeLoop:
        async def run(self, *, goal_description, user_id, db):
            calls["loop"] += 1
            return _persist_goal(
                db,
                goal_description=goal_description,
                user_id=user_id,
                status="completed",
            )

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", unavailable)
    monkeypatch.setattr(
        "backend.aios.autonomous_loop.autonomous_loop_service",
        FakeLoop(),
    )

    payload = {
        "goal": "idempotent submit",
        "user_id": "idempotency-user",
        "idempotency_key": "submit-replay-1",
    }
    first = client.post("/os/submit_goal", json=payload)
    second = client.post("/os/submit_goal", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert calls == {"worker": 1, "loop": 1}


def test_same_key_different_payload_returns_conflict(monkeypatch):
    async def unavailable(_request):
        raise HTTPException(status_code=503, detail="offline")

    class FakeLoop:
        async def run(self, *, goal_description, user_id, db):
            return _persist_goal(
                db,
                goal_description=goal_description,
                user_id=user_id,
                status="completed",
            )

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", unavailable)
    monkeypatch.setattr(
        "backend.aios.autonomous_loop.autonomous_loop_service",
        FakeLoop(),
    )

    base = {
        "goal": "original payload",
        "user_id": "conflict-user",
        "idempotency_key": "conflict-key-1",
    }
    assert client.post("/os/submit_goal", json=base).status_code == 200

    conflict = client.post(
        "/os/submit_goal",
        json={**base, "goal": "different payload"},
    )
    assert conflict.status_code == 409


def test_concurrent_same_key_has_one_reservation():
    scope = "test.concurrent"
    key = "concurrent-key-1"
    fingerprint = "a" * 64

    def reserve():
        db = _db()
        try:
            record, is_new = os_endpoint._reserve_idempotency(
                db,
                scope=scope,
                user_id="concurrent-user",
                key=key,
                fingerprint=fingerprint,
            )
            return record.id, is_new
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))

    assert sorted(is_new for _, is_new in results) == [False, True]
    assert len({record_id for record_id, _ in results}) == 1


def test_concurrent_submit_goal_requests_share_one_operation(monkeypatch):
    calls = 0
    lock = Lock()

    async def worker(_request):
        nonlocal calls
        with lock:
            calls += 1
        return {"task_id": "worker-concurrent-1", "status": "queued"}

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", worker)
    payload = {
        "goal": "concurrent submit",
        "user_id": "concurrent-endpoint-user",
        "idempotency_key": "concurrent-submit-1",
    }

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post("/os/submit_goal", json=payload), range(2)))

    assert {response.status_code for response in responses} <= {200, 202}
    assert calls == 1
    assert {response.json()["status"] for response in responses} <= {"reserved", "queued"}


def test_completed_and_failed_operations_replay_without_worker(monkeypatch):
    db = _db()
    completed = Goal(
        description="completed replay",
        user_id="replay-user",
        status="completed",
    )
    failed = Goal(
        description="failed replay",
        user_id="replay-user",
        status="failed",
    )
    db.add_all([completed, failed])
    db.commit()
    db.refresh(completed)
    db.refresh(failed)
    db.add_all([
        AIOSIdempotencyRecord(
            scope="os.submit_goal",
            user_id="replay-user",
            idempotency_key="completed-replay",
            request_fingerprint=os_endpoint._request_fingerprint(
                "os.submit_goal", "replay-user", {"goal": "completed replay"}
            ),
            status="completed",
            goal_id=completed.id,
        ),
        AIOSIdempotencyRecord(
            scope="os.submit_goal",
            user_id="replay-user",
            idempotency_key="failed-replay",
            request_fingerprint=os_endpoint._request_fingerprint(
                "os.submit_goal", "replay-user", {"goal": "failed replay"}
            ),
            status="failed",
            goal_id=failed.id,
        ),
    ])
    db.commit()
    db.close()

    async def should_not_run(_request):
        raise AssertionError("worker must not run for an existing key")

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", should_not_run)

    completed_response = client.post(
        "/os/submit_goal",
        json={
            "goal": "completed replay",
            "user_id": "replay-user",
            "idempotency_key": "completed-replay",
        },
    )
    failed_response = client.post(
        "/os/submit_goal",
        json={
            "goal": "failed replay",
            "user_id": "replay-user",
            "idempotency_key": "failed-replay",
        },
    )

    assert completed_response.json()["status"] == "completed"
    assert failed_response.json()["status"] == "failed"


def test_execute_async_worker_path_stores_worker_task_id(monkeypatch):
    calls = 0

    async def worker(request):
        nonlocal calls
        calls += 1
        assert request.idempotency_key == "execute-worker-1"
        return {"task_id": "worker-7001", "status": "queued"}

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", worker)

    payload = {
        "command": "execute worker once",
        "user_id": "execute-user",
        "async_mode": True,
        "idempotency_key": "execute-worker-1",
    }
    first = client.post("/os/execute", json=payload)
    second = client.post("/os/execute", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["task_id"] == "worker-7001"
    assert second.json()["task_id"] == "worker-7001"
    assert calls == 1

    db = _db()
    record = db.query(AIOSIdempotencyRecord).filter_by(
        scope="os.execute.async",
        user_id="execute-user",
        idempotency_key="execute-worker-1",
    ).one()
    assert record.worker_task_id == "worker-7001"
    assert record.status == "queued"
    db.close()


def test_execute_async_worker_success_without_task_id_stays_reserved(monkeypatch):
    calls = 0

    async def worker(_request):
        nonlocal calls
        calls += 1
        return {"status": "queued"}

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", worker)
    monkeypatch.setattr(
        os_endpoint,
        "_get_planner",
        lambda: SimpleNamespace(
            create_plan=lambda command, user_id: [[]]
        ),
    )

    payload = {
        "command": "worker response missing task id",
        "user_id": "missing-worker-id-user",
        "async_mode": True,
        "idempotency_key": "missing-worker-id-key",
    }
    first = client.post("/os/execute", json=payload)
    second = client.post("/os/execute", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json().get("task_id") is None
    assert second.json().get("task_id") is None
    assert first.json()["idempotency_record_id"] == second.json()["idempotency_record_id"]
    assert calls == 1

    db = _db()
    record = db.query(AIOSIdempotencyRecord).filter_by(
        scope="os.execute.async",
        user_id="missing-worker-id-user",
        idempotency_key="missing-worker-id-key",
    ).one()
    assert record.status == "reserved"
    assert record.worker_task_id is None
    db.close()


def test_execute_async_local_fallback_stores_goal_id(monkeypatch):
    async def unavailable(_request):
        raise HTTPException(status_code=503, detail="offline")

    class FakeLoop:
        async def run(self, *, goal_description, user_id, db):
            return _persist_goal(
                db,
                goal_description=goal_description,
                user_id=user_id,
                status="failed",
            )

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", unavailable)
    monkeypatch.setattr(
        "backend.aios.autonomous_loop.autonomous_loop_service",
        FakeLoop(),
    )
    monkeypatch.setattr(
        os_endpoint,
        "_get_planner",
        lambda: SimpleNamespace(
            create_plan=lambda command, user_id: [[]]
        ),
    )

    response = client.post(
        "/os/execute",
        json={
            "command": "execute local once",
            "user_id": "execute-local-user",
            "async_mode": True,
            "idempotency_key": "execute-local-1",
        },
    )
    assert response.status_code == 200

    db = _db()
    record = db.query(AIOSIdempotencyRecord).filter_by(
        scope="os.execute.async",
        user_id="execute-local-user",
        idempotency_key="execute-local-1",
    ).one()
    goal = db.get(Goal, record.goal_id)
    assert goal is not None
    assert goal.status == "failed"
    assert record.status == "failed"
    db.close()


def test_sync_execute_does_not_require_idempotency():
    response = client.post(
        "/os/execute",
        json={
            "command": "plan without execution",
            "user_id": "sync-user",
            "async_mode": False,
        },
    )
    assert response.status_code in {200, 500}
    if response.status_code == 200:
        assert response.json()["status"] == "planned"


def test_agent_run_does_not_create_idempotency_record(monkeypatch):
    before = _db().query(AIOSIdempotencyRecord).count()

    class FakeDiscovery:
        async def discover(self, topic):
            return []

    class FakeRanking:
        def rank(self, candidates, *, user_id):
            return candidates

    monkeypatch.setattr(os_endpoint, "_get_discovery", lambda: FakeDiscovery())
    monkeypatch.setattr(os_endpoint, "_get_ranking", lambda: FakeRanking())
    monkeypatch.setattr(
        os_endpoint.intelligence_engine_service,
        "analyze",
        lambda candidates, editorial_intent: candidates,
    )
    monkeypatch.setattr(
        os_endpoint.evaluation_engine_service,
        "evaluate",
        lambda candidates: candidates,
    )

    response = client.post(
        "/os/agent/run",
        json={"agent": "discover", "input": {"topic": "idempotency"}},
    )
    after = _db().query(AIOSIdempotencyRecord).count()

    assert response.status_code == 200
    assert after == before


def test_reserved_record_is_not_silently_reexecuted():
    db = _db()
    record = AIOSIdempotencyRecord(
        scope="os.submit_goal",
        user_id="reserved-user",
        idempotency_key="reserved-key",
        request_fingerprint=os_endpoint._request_fingerprint(
            "os.submit_goal", "reserved-user", {"goal": "reserved goal"}
        ),
        status="reserved",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_id = record.id
    db.close()

    response = client.post(
        "/os/submit_goal",
        json={
            "goal": "reserved goal",
            "user_id": "reserved-user",
            "idempotency_key": "reserved-key",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "reserved"
    assert payload["idempotency_record_id"] == str(record_id)
    assert payload.get("task_id") is None
    assert "result" not in payload
    assert "error" not in payload


def test_reserved_record_replays_bound_worker_task_id(monkeypatch):
    db = _db()
    record = AIOSIdempotencyRecord(
        scope="os.execute.async",
        user_id="reserved-worker-user",
        idempotency_key="reserved-worker-key",
        request_fingerprint=os_endpoint._request_fingerprint(
            "os.execute.async", "reserved-worker-user", {"command": "reserved worker"}
        ),
        status="reserved",
        worker_task_id="worker-queued-123",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    db.close()

    calls = {"submit": 0}

    async def worker(_request):
        calls["submit"] += 1
        raise AssertionError("reserved worker task replay must not execute again")

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", worker)

    response = client.post(
        "/os/execute",
        json={
            "command": "reserved worker",
            "user_id": "reserved-worker-user",
            "async_mode": True,
            "idempotency_key": "reserved-worker-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["task_id"] == "worker-queued-123"
    assert response.json()["status"] == "reserved"
    assert calls == {"submit": 0}


def test_reserved_record_replays_bound_goal_id(monkeypatch):
    db = _db()
    goal = Goal(
        description="reserved goal replay",
        user_id="reserved-goal-user",
        status="running",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    goal_id = goal.id
    record = AIOSIdempotencyRecord(
        scope="os.submit_goal",
        user_id="reserved-goal-user",
        idempotency_key="reserved-goal-key",
        request_fingerprint=os_endpoint._request_fingerprint(
            "os.submit_goal", "reserved-goal-user", {"goal": "reserved goal replay"}
        ),
        status="reserved",
        goal_id=goal.id,
    )
    db.add(record)
    db.commit()
    db.close()

    calls = {"submit": 0}

    async def worker(_request):
        calls["submit"] += 1
        raise AssertionError("reserved goal replay must not execute again")

    monkeypatch.setattr(os_endpoint.worker_client, "submit_task", worker)

    response = client.post(
        "/os/submit_goal",
        json={
            "goal": "reserved goal replay",
            "user_id": "reserved-goal-user",
            "idempotency_key": "reserved-goal-key",
        },
    )

    assert response.status_code == 200
    assert response.json()["task_id"] == str(goal_id)
    assert response.json()["status"] == "running"
    assert calls == {"submit": 0}
