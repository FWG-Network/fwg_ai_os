from pydantic import BaseModel
from typing import List, Optional

# --- Discovery ---
class DiscoveryRequest(BaseModel):
    topic: str
    user_id: str

class ContentCandidate(BaseModel):
    id: str
    title: str
    platform: str
    semantic_score: float
    views: int
    likes: int
    age_days: int
    followers: int
    creator: str
    tags: List[str]

# --- Ranking ---
class RankingResponse(BaseModel):
    title: str
    ranking_score: float
    explanation: str

# --- Personalization ---
class UserProfile(BaseModel):
    user_id: str
    interests: dict = {}
    feedback_score: int = 0

# --- Multimodal ---
class MultimodalResponse(BaseModel):
    text_embedding: Optional[List[float]] = None
    image_embedding: Optional[List[float]] = None
    speech_to_text: Optional[str] = None
    ocr_text: Optional[str] = None


class FeedbackEvent(BaseModel):
    user_id:    str
    item_id:    str
    event_type: str    # "like"|"dislike"|"skip"|"watch_time"|"impression"
    value:      float = 1.0


class TaskRequest(BaseModel):
    goal:    str
    user_id: Optional[str] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status:  str           # "received"|"planning"|"executing"|"completed"|"failed"
    result:  Optional[dict] = None
    error:   Optional[str]  = None

# --- Memory / Knowledge Base ---
class ContentItem(BaseModel):
    id: Optional[str] = None
    text: str
    metadata: Optional[dict] = None
    embedding: Optional[List[float]] = None

class EditorialIntent(BaseModel):
    topic: str
    niche: str
    creative_brief_summary: str
    desired_clip_characteristics: dict | None = None
    reject_content_types: list[str] = []
    target_emotions: list[str] = []
