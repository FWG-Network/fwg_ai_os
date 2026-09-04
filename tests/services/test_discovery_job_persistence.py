"""
Phase 3.5 — Discovery execution persistence contract.

Test-first contract:
- Every SourceHunter execution gets a persisted DiscoveryJob row.
- Job lifecycle: pending -> running -> completed / failed.
- Attempts are persisted.
- Last error is persisted on failure.
- Result count is persisted on completion.
- Timestamps are UTC-aware.
- Persistence must work with the repository's SQLAlchemy/SQLite test DB.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.models.db import Base, DiscoveryJob


@pytest.fixture()
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


def test_discovery_job_can_be_created_with_pending_defaults(db_session):
    job = DiscoveryJob()

    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.id is not None
    assert job.status == "pending"
    assert job.attempts == 0
    assert job.last_error is None
    assert job.result_count == 0
    assert job.created_at is not None


def test_discovery_job_persists_running_state(db_session):
    job = DiscoveryJob(
        status="running",
        attempts=1,
        started_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    db_session.commit()

    stored = db_session.scalars(
        select(DiscoveryJob).where(DiscoveryJob.id == job.id)
    ).one()

    assert stored.status == "running"
    assert stored.attempts == 1
    assert stored.started_at is not None


def test_discovery_job_persists_completed_state_and_result_count(db_session):
    job = DiscoveryJob(
        status="completed",
        attempts=1,
        result_count=12,
        completed_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    db_session.commit()

    stored = db_session.scalars(
        select(DiscoveryJob).where(DiscoveryJob.id == job.id)
    ).one()

    assert stored.status == "completed"
    assert stored.attempts == 1
    assert stored.result_count == 12
    assert stored.completed_at is not None
    assert stored.last_error is None


def test_discovery_job_persists_failed_state_and_error(db_session):
    job = DiscoveryJob(
        status="failed",
        attempts=3,
        last_error="connector unavailable",
        completed_at=datetime.now(timezone.utc),
    )

    db_session.add(job)
    db_session.commit()

    stored = db_session.scalars(
        select(DiscoveryJob).where(DiscoveryJob.id == job.id)
    ).one()

    assert stored.status == "failed"
    assert stored.attempts == 3
    assert stored.last_error == "connector unavailable"
    assert stored.completed_at is not None


def test_discovery_job_does_not_require_result_payload(db_session):
    job = DiscoveryJob(
        status="completed",
        attempts=1,
        result_count=0,
    )

    db_session.add(job)
    db_session.commit()

    stored = db_session.scalars(
        select(DiscoveryJob).where(DiscoveryJob.id == job.id)
    ).one()

    assert stored.result_count == 0
