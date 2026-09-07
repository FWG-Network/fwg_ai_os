from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Discovery
# ============================================================

class DiscoveryRequest(BaseModel):
    topic: str
    user_id: Optional[str] = None


class ContentCandidate(BaseModel):
    id: str
    title: str
    platform: str
    semantic_score: float = 0.0
    views: int = 0
    likes: int = 0
    age_days: int = 0
    followers: int = 0
    creator: str = ""
    tags: List[str] = Field(default_factory=list)


# ============================================================
# Ranking
# ============================================================

class RankingResponse(BaseModel):
    title: str
    ranking_score: float
    explanation: str


# ============================================================
# Personalization
# ============================================================

class UserProfile(BaseModel):
    user_id: str
    interests: Dict[str, Any] = Field(default_factory=dict)
    feedback_score: int = 0


# ============================================================
# Multimodal
# ============================================================

class MultimodalResponse(BaseModel):
    text_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    speech_to_text: Optional[str] = None
    ocr_text: Optional[str] = None


# ============================================================
# Feedback / Learning
# ============================================================

class FeedbackEvent(BaseModel):
    user_id: str
    item_id: str
    event_type: str
    value: float = 1.0


# ============================================================
# Task / OS
# ============================================================

class TaskRequest(BaseModel):
    goal: str
    user_id: Optional[str] = None
    idempotency_key: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: Optional[str] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    idempotency_record_id: Optional[str] = None


# ============================================================
# Memory / Knowledge Base
# ============================================================

class ContentItem(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None
    platform: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None

    @property
    def item_id(self) -> Optional[str]:
        """Backward-compatible identifier used by existing consumers."""
        return self.id


# ============================================================
# Editorial / Discovery Intelligence
# ============================================================

class EditorialIntent(BaseModel):
    topic: str
    niche: str
    creative_brief_summary: str
    desired_clip_characteristics: Optional[Dict[str, Any]] = None
    reject_content_types: List[str] = Field(default_factory=list)
    target_emotions: List[str] = Field(default_factory=list)


class MomentType(BaseModel):
    name: str
    keywords: List[str] = Field(default_factory=list)


class SceneType(BaseModel):
    name: str
    visual_cues: List[str] = Field(default_factory=list)


class MomentOntologyCategory(BaseModel):
    category: str
    moment_types: List[MomentType] = Field(default_factory=list)
    scene_types: List[SceneType] = Field(default_factory=list)


class MomentOntology(BaseModel):
    ontology: List[MomentOntologyCategory] = Field(default_factory=list)


class PlatformStrategy(BaseModel):
    platform: str
    search_approach: str
    primary_queries: Optional[List[str]] = None
    secondary_queries: Optional[List[str]] = None
    hashtags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    filters: Dict[str, Any] = Field(default_factory=dict)


class DiscoveryMission(BaseModel):
    mission_focus: str
    clip_criteria: Dict[str, Any]
    priority_score: int
    confidence_score: int
    estimated_cost: str
    expected_yield: str
    platform_strategies: List[PlatformStrategy] = Field(
        default_factory=list
    )


# ============================================================
# Source Hunter
# ============================================================

class RawClip(BaseModel):
    id: str
    url: str
    title: str
    platform: str
    channel: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    views: Optional[int] = None
    likes: Optional[int] = None
    engagement_rate: Optional[float] = None
    published_at: Optional[str] = None
    observed_metrics: Dict[str, Any] = Field(default_factory=dict)
    metric_schema_version: Optional[str] = None


class SourceHunterResult(BaseModel):
    clips: List[RawClip] = Field(default_factory=list)
    provenance: Dict[str, List[Dict[str, Any]]] = Field(
        default_factory=dict
    )
