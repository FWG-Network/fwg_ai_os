"""
Gate D — Source Hunter -> ContentCandidate adapter.

Converts SourceHunterResult / RawClip objects into the legacy
ContentCandidate contract without mutating the source objects.

age_days V1 semantics:
- valid timestamp -> elapsed whole days from reference_time
- None / malformed -> 10
- future timestamp -> 0
- "Z" suffix -> UTC
- explicit offsets -> preserved and compared by absolute instant
- naive timestamp -> interpreted as UTC
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.models.schemas import (
    ContentCandidate,
    RawClip,
    SourceHunterResult,
)


_UNKNOWN_AGE_DAYS = 10


def _parse_published_at(value: str) -> datetime | None:
    """Parse an ISO-8601 timestamp into an aware UTC datetime.

    Naive timestamps are interpreted as UTC per the V1 contract.
    Invalid values return None.
    """
    try:
        text = value.strip()
        if not text:
            return None

        # Python 3.11+ accepts most ISO-8601 forms but historically does
        # not treat trailing "Z" uniformly across supported runtimes.
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"

        parsed = datetime.fromisoformat(text)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)

        return parsed
    except (TypeError, ValueError, OverflowError):
        return None


def _age_days(
    published_at: str | None,
    *,
    reference_time: datetime | None,
) -> int:
    """Calculate non-negative elapsed whole days under the V1 contract."""
    if not published_at:
        return _UNKNOWN_AGE_DAYS

    published = _parse_published_at(published_at)
    if published is None:
        return _UNKNOWN_AGE_DAYS

    if reference_time is None:
        reference = datetime.now(timezone.utc)
    elif reference_time.tzinfo is None:
        # V1 policy: a naive reference time is interpreted as UTC.
        reference = reference_time.replace(tzinfo=timezone.utc)
    else:
        reference = reference_time.astimezone(timezone.utc)

    elapsed_seconds = (reference - published).total_seconds()

    if elapsed_seconds <= 0:
        return 0

    return int(elapsed_seconds // 86400)


def _adapt_clip(
    clip: RawClip,
    *,
    reference_time: datetime | None,
) -> ContentCandidate:
    """Adapt one RawClip without mutating it."""
    return ContentCandidate(
        id=clip.id,
        title=clip.title,
        platform=clip.platform,
        views=0 if clip.views is None else clip.views,
        likes=0 if clip.likes is None else clip.likes,
        age_days=_age_days(
            clip.published_at,
            reference_time=reference_time,
        ),
        creator=clip.channel or "",
        tags=list(clip.tags),
    )


def adapt_source_hunter_result(
    result: SourceHunterResult,
    *,
    reference_time: datetime | None = None,
) -> list[ContentCandidate]:
    """Convert SourceHunterResult clips into ContentCandidate objects.

    Input order is preserved. The source result and its RawClip objects are
    never mutated.
    """
    return [
        _adapt_clip(clip, reference_time=reference_time)
        for clip in result.clips
    ]
