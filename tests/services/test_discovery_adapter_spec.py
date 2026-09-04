"""
Gate D — Adapter contract tests (test-first, pre-implementation).

Tests the VOF-approved interface:
    adapt_source_hunter_result(result, *, reference_time=None) -> list[ContentCandidate]

No production adapter exists yet (backend/services/discovery_adapter.py).
These tests are expected to FAIL (ImportError) until that file is created,
per strict test-first workflow.

age_days V1 contract (VOF-approved):
    valid tz-aware timestamp -> elapsed whole days from reference_time
    published_at is None      -> age_days = 10  (matches RankingEngine's
                                                   existing unknown-age fallback)
    malformed/unparseable      -> age_days = 10
    valid future timestamp     -> age_days = 0   (not "unknown"; clock-skew safe)
    "Z" suffix                 -> parsed as UTC
    "+00:00"/offset            -> offset preserved
    naive (no tzinfo)          -> interpreted as UTC for V1 (documented here)
"""
import pytest
from datetime import datetime, timezone, timedelta

from backend.models.schemas import RawClip, SourceHunterResult, ContentCandidate
from backend.services.discovery_adapter import adapt_source_hunter_result


# ---- Fixed reference time (no wall-clock dependency) -----------------------
REFERENCE_TIME = datetime(2026, 8, 17, 12, 0, 0, tzinfo=timezone.utc)


def _iso_days_ago(days: int, tz_style: str = "offset") -> str:
    dt = REFERENCE_TIME - timedelta(days=days)
    if tz_style == "z":
        return dt.isoformat().replace("+00:00", "Z")
    if tz_style == "naive":
        return dt.replace(tzinfo=None).isoformat()
    return dt.isoformat()


# ---- Fixtures ---------------------------------------------------------------
@pytest.fixture
def full_raw_clip():
    return RawClip(
        id="clip_123",
        url="https://youtube.com/watch?v=abc123",
        title="Amazing AI Trend Breakdown",
        platform="youtube",
        channel="TechChannel",
        tags=["ai", "trends"],
        views=50000,
        likes=3200,
        engagement_rate=0.064,
        published_at=_iso_days_ago(5),
        observed_metrics={"shares": 120, "comments": 45},
        metric_schema_version="v1.0",
    )


@pytest.fixture
def minimal_raw_clip():
    return RawClip(
        id="clip_min",
        url="https://youtube.com/watch?v=min",
        title="Minimal Clip",
        platform="youtube",
    )


@pytest.fixture
def source_hunter_result(full_raw_clip, minimal_raw_clip):
    return SourceHunterResult(
        clips=[full_raw_clip, minimal_raw_clip],
        provenance={
            "mission_1": [{"query": "AI trends", "platform": "youtube", "matched": 2}]
        },
    )


# ---- Direct field mapping (adapter OUTPUT, not just fixture input) ---------
def test_adapter_maps_id_url_title_platform_directly(full_raw_clip):
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)

    assert len(candidates) == 1
    c = candidates[0]
    assert isinstance(c, ContentCandidate)
    assert c.id == "clip_123"
    assert c.title == "Amazing AI Trend Breakdown"
    assert c.platform == "youtube"


def test_adapter_maps_channel_to_creator(full_raw_clip):
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].creator == "TechChannel"


def test_adapter_maps_tags_views_likes(full_raw_clip):
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    c = candidates[0]
    assert c.tags == ["ai", "trends"]
    assert c.views == 50000
    assert c.likes == 3200


# ---- age_days V1 contract ----------------------------------------------------
def test_age_days_valid_timestamp_five_days_ago(full_raw_clip):
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 5


def test_age_days_none_falls_back_to_ten(minimal_raw_clip):
    assert minimal_raw_clip.published_at is None
    result = SourceHunterResult(clips=[minimal_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 10


def test_age_days_malformed_falls_back_to_ten():
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at="not-a-real-date")
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 10


def test_age_days_future_timestamp_clamped_to_zero():
    future = (REFERENCE_TIME + timedelta(days=3)).isoformat()
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at=future)
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 0


def test_age_days_z_suffix_parsed_as_utc():
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at=_iso_days_ago(7, tz_style="z"))
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 7


def test_age_days_nonzero_offset_converted_correctly():
    """Real non-UTC offset (+07:00) must be converted to the correct
    UTC instant before computing elapsed days, not treated as UTC as-is.

    published_at = 2026-08-12T19:00:00+07:00  ==  2026-08-12T12:00:00Z
    reference_time = 2026-08-17T12:00:00Z
    elapsed = exactly 5 whole days
    """
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at="2026-08-12T19:00:00+07:00")
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 5


def test_age_days_naive_timestamp_interpreted_as_utc():
    """V1 documented policy: naive (no tzinfo) timestamps are treated as UTC."""
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at=_iso_days_ago(4, tz_style="naive"))
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days == 4


def test_age_days_never_left_as_pydantic_default_zero_for_unknown():
    """Guards against silently relying on ContentCandidate.age_days=0 default,
    which would make an unknown-age clip look maximally fresh."""
    clip = RawClip(id="c1", url="u", title="t", platform="youtube",
                    published_at=None)
    result = SourceHunterResult(clips=[clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates[0].age_days != 0
    assert candidates[0].age_days == 10


# ---- Empty / multiple clips ---------------------------------------------------
def test_adapter_handles_empty_clips_list():
    result = SourceHunterResult(clips=[], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert candidates == []


def test_adapter_handles_multiple_clips_preserving_order(source_hunter_result):
    candidates = adapt_source_hunter_result(source_hunter_result, reference_time=REFERENCE_TIME)
    assert len(candidates) == 2
    assert candidates[0].id == "clip_123"
    assert candidates[1].id == "clip_min"


# ---- Optional field handling ---------------------------------------------------
def test_adapter_handles_missing_optional_fields_gracefully(minimal_raw_clip):
    """ContentCandidate.views is a plain `int = 0` (non-Optional) field.
    When RawClip.views is None, the adapter must explicitly write 0,
    matching the schema's own declared default -- pinned exactly, no OR."""
    result = SourceHunterResult(clips=[minimal_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    c = candidates[0]
    assert c.id == "clip_min"
    assert c.tags == []
    assert c.views == 0


# ---- reference_time defaults when omitted --------------------------------------
def test_reference_time_defaults_to_now_when_omitted(full_raw_clip):
    """If reference_time is not passed, implementation must use current UTC
    time rather than raise -- this test only checks it doesn't error and
    produces a non-negative age_days."""
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    candidates = adapt_source_hunter_result(result)
    assert candidates[0].age_days >= 0


# ---- Internal rich-data preservation (must NOT be mutated/destroyed) -----------
def test_source_raw_clip_engagement_rate_untouched_after_adapt(full_raw_clip):
    original = full_raw_clip.engagement_rate
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert full_raw_clip.engagement_rate == original == 0.064


def test_source_raw_clip_observed_metrics_untouched_after_adapt(full_raw_clip):
    original = dict(full_raw_clip.observed_metrics)
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert full_raw_clip.observed_metrics == original


def test_source_raw_clip_metric_schema_version_untouched_after_adapt(full_raw_clip):
    result = SourceHunterResult(clips=[full_raw_clip], provenance={})
    adapt_source_hunter_result(result, reference_time=REFERENCE_TIME)
    assert full_raw_clip.metric_schema_version == "v1.0"


def test_source_hunter_result_provenance_untouched_after_adapt(source_hunter_result):
    original = dict(source_hunter_result.provenance)
    adapt_source_hunter_result(source_hunter_result, reference_time=REFERENCE_TIME)
    assert source_hunter_result.provenance == original
