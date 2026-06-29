"""
backend/learning/events.py
Event types + UserEvent schema.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel


class EventType(str, Enum):
    VIEW       = "view"
    CLICK      = "click"
    WATCH      = "watch_time"   # ✅ Fix: "watch_time" matches FeedbackEvent + reward.py
    LIKE       = "like"
    SAVE       = "save"
    SHARE      = "share"
    FOLLOW     = "follow"
    SKIP       = "skip"
    DISLIKE    = "dislike"      # ✅ Added: matches reward.py
    IMPRESSION = "impression"   # ✅ Added: matches reward.py


class UserEvent(BaseModel):
    user_id:    str
    item_id:    str
    event_type: EventType
    tags:       List[str]        = []
    value:      float            = 0.0   # e.g. watch_time ratio 0.0→1.0

    # ✅ Added: item metadata for PersonalizationEngine signal extraction
    platform:   Optional[str]   = None
    channel:    Optional[str]   = None
    category:   Optional[str]   = None
