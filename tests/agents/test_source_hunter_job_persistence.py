"""
Phase 3.5 — SourceHunter execution persistence lifecycle.

Contract:
- hunt(..., db=session) creates one DiscoveryJob.
- Job starts as pending, then running.
- First execution attempt is persisted as attempts=1.
- Successful execution becomes completed.
- result_count equals unique returned clips.
- started_at and completed_at are persisted.
- Existing standalone hunt(...), without db, remains backward compatible.
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


@pytest.fixture
def mock_discovery_engine():
    mock = AsyncMock()
    mock.discover_from_strategy.return_value = [
        {
            "id": "clip-1",
            "url": "https://youtube.com/watch?v=clip-1",
            "title": "Test Clip",
            "platform": "youtube",
        },
        {
            "id": "clip-2",
            "url": "https://youtube.com/watch?v=clip-2",
            "title": "Test Clip 2",
            "platform": "youtube",
        },
    ]
    return mock


def make_mission():
    return DiscoveryMission(
        mission_focus="Persistence test",
        clip_criteria={},
        priority_score=80,
        confidence_score=80,
        estimated_cost="Low",
        expected_yield="High",
        platform_strategies=[
            PlatformStrategy(
                platform="youtube",
                search_approach="Event-specific",
                primary_queries=["test query"],
                secondary_queries=[],
                hashtags=[],
                keywords=[],
                filters={},
            )
        ],
    )


@pytest.mark.asyncio
async def test_hunt_persists_completed_discovery_job(
    db_session,
    mock_discovery_engine,
):
    agent = SourceHunterAgent(
        discovery_engine=mock_discovery_engine,
    )

    result = await agent.hunt(
        [make_mission()],
        db=db_session,
    )

    assert len(result.clips) == 2

    jobs = db_session.scalars(
        select(DiscoveryJob)
    ).all()

    assert len(jobs) == 1

    job = jobs[0]
    assert job.status == "completed"
    assert job.attempts == 1
    assert job.result_count == 2
    assert job.last_error is None
    assert job.started_at is not None
    assert job.completed_at is not None
    assert job.created_at is not None


@pytest.mark.asyncio
async def test_hunt_without_db_remains_backward_compatible(
    mock_discovery_engine,
):
    agent = SourceHunterAgent(
        discovery_engine=mock_discovery_engine,
    )

    result = await agent.hunt([make_mission()])

    assert len(result.clips) == 2
    mock_discovery_engine.discover_from_strategy.assert_called_once()
