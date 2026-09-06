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
