from pydantic import BaseModel
from enum import Enum
from typing import List

class EventType(str, Enum):
    VIEW = "view"
    CLICK = "click"
    WATCH = "watch" # Can have a value for watch time percentage
    LIKE = "like"
    SAVE = "save"
    SHARE = "share"
    FOLLOW = "follow"
    SKIP = "skip"

class UserEvent(BaseModel):
    user_id: str
    item_id: str
    event_type: EventType
    tags: List[str] # Tags of the item involved in the event
    value: float = 0.0 # Optional value, e.g., watch_time_ratio
