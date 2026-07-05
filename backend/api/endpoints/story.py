"""
backend/api/endpoints/story.py

⚠️ STATUS: NEW FILE — no prior version existed (confirmed via `find` in repo).
UNTESTED — depends on story_learning_engine.py + llm_router.py v3, neither of
which have been execution-tested against live API keys in this sandbox.

Endpoints:
  POST /api/v1/story/learn_channel   — analyze sample videos, extract pattern
  POST /api/v1/story/generate_series — generate next episode script + prompts

Follows the same safe-import + APIRouter convention as other endpoints
(backend/api/endpoints/discovery.py etc. per README.pdf's documented pattern).
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.logger import log
from backend.services.story_learning_engine import story_learning_engine

router = APIRouter(prefix="/story", tags=["Story Learning Engine"])


# ── Request/response schemas ────────────────────────────────────────────
# NOTE: defined locally here rather than in backend/models/schemas.py because
# that file's current contents weren't available to verify against — move
# these into schemas.py if project convention requires central schema
# definitions (flag for Dev 2 to confirm).

class LearnChannelRequest(BaseModel):
    channel_name: str = Field(..., description="Reference channel name, e.g. 'MeowFlix'")
    sample_transcripts: list[str] = Field(
        ..., min_length=1,
        description="Raw text per sample video: transcript, caption, or scene description. "
                    "This endpoint does not fetch video data itself — caller supplies it."
    )


class LearnChannelResponse(BaseModel):
    channel_name: str
    sample_count: int
    patterns: Optional[dict[str, Any]]
    answered_by: str
    evidence: str  # "measured" | "unavailable" — never a fabricated placeholder


class CharacterModel(BaseModel):
    name: str
    visual_description: str


class SeriesState(BaseModel):
    characters: list[CharacterModel] = Field(default_factory=list)
    prior_episode_summaries: list[str] = Field(default_factory=list)


class GenerateSeriesRequest(BaseModel):
    channel_name: str
    learned_patterns: dict[str, Any] = Field(
        ..., description="Output of /story/learn_channel's 'patterns' field. "
                          "Caller must check evidence=='measured' before sending this."
    )
    series_state: SeriesState
    episode_number: int = Field(..., ge=1)


class GenerateSeriesResponse(BaseModel):
    episode_number: int
    script: Optional[str]
    sora_prompts: Optional[list[str]]
    answered_by: str
    evidence: str


# ── Endpoints ────────────────────────────────────────────────────────────
@router.post("/learn_channel", response_model=LearnChannelResponse)
async def learn_channel(request: LearnChannelRequest) -> LearnChannelResponse:
    """
    Analyze sample video transcripts from a reference channel and extract
    the recurring structural pattern (opening hook, conflict, cliffhanger,
    recurring characters).

    Evidence-First: if the LLM fails or returns unparseable output, this
    returns patterns=None and evidence="unavailable" — it does NOT fabricate
    a plausible-looking pattern.
    """
    log.info(f"[story.learn_channel] channel={request.channel_name} "
             f"samples={len(request.sample_transcripts)}")

    result = await story_learning_engine.learn_channel_patterns(
        channel_name=request.channel_name,
        sample_transcripts=request.sample_transcripts,
    )
    return LearnChannelResponse(**result)


@router.post("/generate_series", response_model=GenerateSeriesResponse)
async def generate_series(request: GenerateSeriesRequest) -> GenerateSeriesResponse:
    """
    Generate the next episode's script + Sora-ready prompts, preserving
    character consistency from series_state.

    Refuses to generate (returns evidence="unavailable") if learned_patterns
    is empty — never writes a script from an unmeasured/guessed pattern.
    """
    if not request.learned_patterns:
        raise HTTPException(
            status_code=422,
            detail="learned_patterns is empty — call /story/learn_channel first "
                   "and confirm evidence=='measured' before generating an episode."
        )

    log.info(f"[story.generate_series] channel={request.channel_name} "
             f"episode={request.episode_number}")

    result = await story_learning_engine.generate_next_episode(
        channel_name=request.channel_name,
        learned_patterns=request.learned_patterns,
        series_state=request.series_state.model_dump(),
        episode_number=request.episode_number,
    )
    return GenerateSeriesResponse(**result)
