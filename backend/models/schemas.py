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
