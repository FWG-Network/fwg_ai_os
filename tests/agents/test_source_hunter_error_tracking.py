"""
Phase 3.5 — SourceHunter retry/error tracking contract.

Contract:
- Query-level failures do not abort remaining queries.
- Partial failure still completes the DiscoveryJob.
- Partial failure records the error in last_error.
- If every executable query fails, the DiscoveryJob is failed.
- A single hunt execution counts as attempts=1.
- No automatic retry is introduced by this contract.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.agents.source_hunter_agent import SourceHunterAgent
from backend.models.db import Base, DiscoveryJob
from backend.models.schemas import DiscoveryMission, PlatformStrategy


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def make_mission(queries: list[str]) -> DiscoveryMission:
    return DiscoveryMission(
        mission_focus="Error tracking test",
        clip_criteria={},
        priority_score=80,
        confidence_score=80,
        estimated_cost="Low",
        expected_yield="High",
        platform_strategies=[
            PlatformStrategy(
                platform="youtube",
                search_approach="Event-specific",
                primary_queries=queries,
                secondary_queries=[],
                hashtags=[],
                keywords=[],
                filters={},
            )
        ],
    )


@pytest.mark.asyncio
async def test_partial_query_failure_is_completed_and_tracked(
    db_session,
):
    discovery_engine = AsyncMock()

    async def side_effect(query, filters, platform=None):
        if query == "bad query":
            raise RuntimeError("connector unavailable")

        return [
            {
                "id": "clip-good",
                "url": "https://youtube.com/watch?v=clip-good",
                "title": "Good Clip",
                "platform": "youtube",
            }
        ]

    discovery_engine.discover_from_strategy.side_effect = side_effect

    agent = SourceHunterAgent(
        discovery_engine=discovery_engine,
    )

    result = await agent.hunt(
        [make_mission(["bad query", "good query"])],
        db=db_session,
    )

    assert len(result.clips) == 1

    job = db_session.scalars(
        select(DiscoveryJob)
    ).one()

    assert job.status == "completed"
    assert job.attempts == 1
    assert job.result_count == 1
    assert job.last_error is not None
    assert "connector unavailable" in job.last_error
    assert job.started_at is not None
    assert job.completed_at is not None

    assert discovery_engine.discover_from_strategy.await_count == 2


@pytest.mark.asyncio
async def test_all_query_failures_mark_job_failed(
    db_session,
):
    discovery_engine = AsyncMock()

    async def side_effect(query, filters, platform=None):
        raise RuntimeError(f"failure for {query}")

    discovery_engine.discover_from_strategy.side_effect = side_effect

    agent = SourceHunterAgent(
        discovery_engine=discovery_engine,
    )

    result = await agent.hunt(
        [make_mission(["bad query 1", "bad query 2"])],
        db=db_session,
    )

    assert len(result.clips) == 0

    job = db_session.scalars(
        select(DiscoveryJob)
    ).one()

    assert job.status == "failed"
    assert job.attempts == 1
    assert job.result_count == 0
    assert job.last_error is not None
    assert "failure for bad query" in job.last_error
    assert job.started_at is not None
    assert job.completed_at is not None

    assert discovery_engine.discover_from_strategy.await_count == 2
