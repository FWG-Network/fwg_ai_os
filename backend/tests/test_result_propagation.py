from types import SimpleNamespace

import pytest

from backend.aios.autonomous_loop import AutonomousLoop
from backend.aios.executor import executor_service


class FakeDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)


def make_task(
    task_id,
    *,
    tool_name="trend_analyzer",
    tool_params=None,
    status="pending",
    result=None,
    description="test task",
):
    return SimpleNamespace(
        id=task_id,
        tool_name=tool_name,
        tool_params=tool_params or {},
        status=status,
        result=result,
        description=description,
    )


def test_stage1_result_is_propagated_to_stage2_executor(monkeypatch):
    """
    Contract:
        Stage 1 result["videos"]
            -> input_from.execution_key/result_path
            -> Stage 2 resolved_inputs["candidates"]
            -> Executor uses exact value.
    """
    loop = AutonomousLoop()
    db = FakeDB()

    producer = make_task(
        101,
        tool_name="trend_scanner",
        tool_params={"execution_key": "trend_scan"},
        status="completed",
        result={
            "tool": "trend_scanner",
            "videos": [
                "stage-1-output-A",
                "stage-1-output-B",
            ],
        },
    )

    consumer = make_task(
        102,
        tool_name="trend_analyzer",
        tool_params={
            "input_from": {
                "execution_key": "trend_scan",
                "result_path": "videos",
                "input_name": "candidates",
            }
        },
    )

    registry = {"trend_scan": producer}

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        registry,
        db,
    )

    expected_candidates = [
        "stage-1-output-A",
        "stage-1-output-B",
    ]

    assert resolved == {
        consumer.id: {
            "candidates": expected_candidates,
        }
    }
    assert consumer.status == "pending"

    captured = {}

    class FakeRankingService:
        def rank(self, candidates, *, user_id):
            captured["candidates"] = candidates
            captured["user_id"] = user_id
            return candidates

    from backend.services import ranking_engine

    monkeypatch.setattr(
        ranking_engine,
        "ranking_engine_service",
        FakeRankingService(),
    )


    import asyncio

    result = asyncio.run(
        executor_service.execute_task(
            consumer,
            db,
            user_id="test-user",
            resolved_inputs=resolved[consumer.id],
        )
    )

    assert captured["candidates"] == expected_candidates
    assert captured["user_id"] == "test-user"
    assert result == {
        "tool": "trend_analyzer",
        "total": 2,
        "results": expected_candidates,
    }


def test_dependency_not_found():
    loop = AutonomousLoop()
    db = FakeDB()

    consumer = make_task(
        201,
        tool_params={
            "input_from": {
                "execution_key": "missing",
                "result_path": "videos",
                "input_name": "candidates",
            }
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_not_found",
        "dependency": "missing",
    }


def test_dependency_failed():
    loop = AutonomousLoop()
    db = FakeDB()

    producer = make_task(
        301,
        tool_name="trend_scanner",
        tool_params={"execution_key": "trend_scan"},
        status="failed",
        result={"error": "upstream failure"},
    )

    consumer = make_task(
        302,
        tool_params={
            "input_from": {
                "execution_key": "trend_scan",
                "result_path": "videos",
                "input_name": "candidates",
            }
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {"trend_scan": producer},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_failed",
        "dependency": "trend_scan",
    }


def test_dependency_result_missing():
    loop = AutonomousLoop()
    db = FakeDB()

    producer = make_task(
        401,
        tool_name="trend_scanner",
        tool_params={"execution_key": "trend_scan"},
        status="completed",
        result=None,
    )

    consumer = make_task(
        402,
        tool_params={
            "input_from": {
                "execution_key": "trend_scan",
                "result_path": "videos",
                "input_name": "candidates",
            }
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {"trend_scan": producer},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_result_missing",
        "dependency": "trend_scan",
    }


def test_dependency_result_malformed():
    loop = AutonomousLoop()
    db = FakeDB()

    producer = make_task(
        501,
        tool_name="trend_scanner",
        tool_params={"execution_key": "trend_scan"},
        status="completed",
        result={
            "tool": "trend_scanner",
            "videos": [],
        },
    )

    consumer = make_task(
        502,
        tool_params={
            "input_from": {
                "execution_key": "trend_scan",
                "result_path": "missing.path",
                "input_name": "candidates",
            }
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {"trend_scan": producer},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_result_malformed",
        "dependency": "trend_scan",
        "expected_path": "missing.path",
    }


def test_malformed_dependency_contract():
    loop = AutonomousLoop()
    db = FakeDB()

    consumer = make_task(
        601,
        tool_params={
            "input_from": {
                "execution_key": "trend_scan",
                "input_name": "candidates",
                # result_path intentionally missing
            }
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_result_malformed",
        "dependency": "trend_scan",
        "expected_path": "",
    }


def test_task_without_input_from_remains_backward_compatible():
    loop = AutonomousLoop()
    db = FakeDB()

    task = make_task(
        701,
        tool_name="trend_scanner",
        tool_params={"theme_keyword": "viral trends"},
    )

    resolved = loop._resolve_stage_dependencies(
        [task],
        {},
        db,
    )

    assert resolved == {}
    assert task.status == "pending"
    assert task.result is None


def test_non_dict_input_from_is_malformed_dependency():
    loop = AutonomousLoop()
    db = FakeDB()

    consumer = make_task(
        801,
        tool_params={
            "input_from": "trend_scan",
        },
    )

    resolved = loop._resolve_stage_dependencies(
        [consumer],
        {},
        db,
    )

    assert resolved == {}
    assert consumer.status == "failed"
    assert consumer.result == {
        "error": "dependency_result_malformed",
        "dependency": "",
        "expected_path": "",
    }


@pytest.mark.asyncio
async def test_failed_stage_stops_later_stages_and_reflection_sets_goal_status(monkeypatch):
    from backend.aios.executor import executor_service
    from backend.aios.reflection import reflection_service
    from backend.aios.task_planner import task_planner_service
    from backend.models.db import Goal as GoalModel, SessionLocal, Task as TaskModel

    loop = AutonomousLoop()
    db = SessionLocal()
    stage_calls = []
    reflection_calls = []

    def plan(_description, goal_id):
        return [
            [TaskModel(
                description="stage one",
                goal_id=goal_id,
                tool_name="trend_scanner",
            )],
            [TaskModel(
                description="stage two",
                goal_id=goal_id,
                tool_name="trend_analyzer",
            )],
        ]

    async def fail_stage_one(tasks, db, user_id, execution_context=None):
        stage_calls.append(tasks[0].tool_name)
        tasks[0].status = "failed"
        tasks[0].result = {"error": "stage one failed"}

    original_reflection = reflection_service.evaluate

    def reflection_spy(goal):
        reflection_calls.append(goal.id)
        return original_reflection(goal)

    monkeypatch.setattr(task_planner_service, "create_plan", plan)
    monkeypatch.setattr(
        executor_service,
        "execute_task_group",
        fail_stage_one,
    )
    monkeypatch.setattr(reflection_service, "evaluate", reflection_spy)

    try:
        goal = await loop.run(
            goal_description="strict stage failure stop",
            user_id="test-user",
            db=db,
        )

        assert stage_calls == ["trend_scanner"]
        assert reflection_calls == [goal.id]
        assert goal.status == "failed"
        assert goal.tasks[0].status == "failed"
        assert goal.tasks[0].result == {"error": "stage one failed"}
        assert goal.tasks[1].status == "pending"
    finally:
        persisted = db.get(GoalModel, goal.id)
        if persisted is not None:
            for task in persisted.tasks:
                db.delete(task)
            db.delete(persisted)
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_reflection_exception_fails_goal_and_persists_structured_result(monkeypatch):
    from backend.aios.reflection import reflection_service
    from backend.aios.task_planner import task_planner_service
    from backend.models.db import Goal as GoalModel, SessionLocal, Task as TaskModel

    loop = AutonomousLoop()
    db = SessionLocal()
    goal = None

    def plan(_description, goal_id):
        return [[TaskModel(description="one task", goal_id=goal_id, tool_name="test")]]

    async def complete_stage(tasks, db, user_id, execution_context=None):
        tasks[0].status = "completed"
        tasks[0].result = {"output": "ok"}

    def fail_reflection(_goal):
        raise RuntimeError("reflection unavailable")

    monkeypatch.setattr(task_planner_service, "create_plan", plan)
    monkeypatch.setattr(executor_service, "execute_task_group", complete_stage)
    monkeypatch.setattr(reflection_service, "evaluate", fail_reflection)

    try:
        goal = await loop.run("reflection failure", "test-user", db)
        persisted = db.get(GoalModel, goal.id)
        failure = persisted.tasks[-1]
        assert persisted.status == "failed"
        assert failure.result == {
            "error": "lifecycle_failure",
            "phase": "reflection",
            "exception_type": "RuntimeError",
            "message": "reflection unavailable",
        }
        assert persisted.status != "completed"
    finally:
        if goal is not None:
            persisted = db.get(GoalModel, goal.id)
            for task in persisted.tasks:
                db.delete(task)
            db.delete(persisted)
            db.commit()
        db.close()


@pytest.mark.asyncio
async def test_planner_exception_fails_and_persists_goal(monkeypatch):
    from backend.aios.task_planner import task_planner_service
    from backend.models.db import Goal as GoalModel, SessionLocal

    loop = AutonomousLoop()
    db = SessionLocal()
    goal = None

    def fail_planner(_description, _goal_id):
        raise ValueError("planner unavailable")

    monkeypatch.setattr(task_planner_service, "create_plan", fail_planner)

    try:
        goal = await loop.run("planner failure", "test-user", db)
        persisted = db.get(GoalModel, goal.id)
        assert persisted.status == "failed"
        assert persisted.tasks[0].result["phase"] == "planning"
        assert persisted.tasks[0].result["message"] == "planner unavailable"
    finally:
        if goal is not None:
            persisted = db.get(GoalModel, goal.id)
            for task in persisted.tasks:
                db.delete(task)
            db.delete(persisted)
            db.commit()
        db.close()


def test_stale_running_goal_is_marked_failed():
    from backend.models.db import (
        Goal as GoalModel,
        SessionLocal,
        mark_interrupted_goals_failed,
    )

    db = SessionLocal()
    goal = GoalModel(description="stale goal", user_id="test-user", status="running")
    db.add(goal)
    db.commit()
    db.refresh(goal)

    try:
        assert mark_interrupted_goals_failed(db) == 1
        persisted = db.get(GoalModel, goal.id)
        assert persisted.status == "failed"
        assert persisted.tasks[0].result["error"] == "interrupted_goal_recovered"
    finally:
        persisted = db.get(GoalModel, goal.id)
        for task in persisted.tasks:
            db.delete(task)
        db.delete(persisted)
        db.commit()
        db.close()


@pytest.mark.asyncio
async def test_successful_stage_allows_next_stage_execution(monkeypatch):
    from backend.aios.executor import executor_service
    from backend.aios.task_planner import task_planner_service
    from backend.models.db import Goal as GoalModel, SessionLocal, Task as TaskModel

    loop = AutonomousLoop()
    db = SessionLocal()
    stage_calls = []

    def plan(_description, goal_id):
        return [
            [TaskModel(
                description="stage one",
                goal_id=goal_id,
                tool_name="trend_scanner",
            )],
            [TaskModel(
                description="stage two",
                goal_id=goal_id,
                tool_name="trend_analyzer",
            )],
        ]

    async def complete_stage(tasks, db, user_id, execution_context=None):
        stage_calls.append(tasks[0].tool_name)
        for task in tasks:
            task.status = "completed"
            task.result = {"output": f"stage-{task.id}"}

    monkeypatch.setattr(task_planner_service, "create_plan", plan)
    monkeypatch.setattr(
        executor_service,
        "execute_task_group",
        complete_stage,
    )

    try:
        goal = await loop.run(
            goal_description="successful stage continuation",
            user_id="test-user",
            db=db,
        )

        assert stage_calls == ["trend_scanner", "trend_analyzer"]
        assert goal.status == "completed"
        assert all(task.status == "completed" for task in goal.tasks)
    finally:
        persisted = db.get(GoalModel, goal.id)
        if persisted is not None:
            for task in persisted.tasks:
                db.delete(task)
            db.delete(persisted)
        db.commit()
        db.close()
