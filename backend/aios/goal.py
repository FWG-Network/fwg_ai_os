"""
backend/aios/goal.py
In-memory Goal/Task schemas (Pydantic).

⚠️ NOTE: For DB-persisted goals use GoalModel/TaskModel from backend.models.db
         These Pydantic models are for in-memory/API use only.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import uuid


class Task(BaseModel):
    """In-memory task (not persisted to DB)."""
    id:          str            = Field(default_factory=lambda: f"task_{uuid.uuid4()}")
    description: str
    tool_name:   Optional[str]  = None
    tool_params: Optional[dict] = None
    status:      str            = "pending"
    result:      Optional[Any]  = None   # ✅ Any — supports dict results


class Goal(BaseModel):
    """In-memory goal (not persisted to DB)."""
    id:          str            = Field(default_factory=lambda: f"goal_{uuid.uuid4()}")
    description: str
    user_id:     Optional[str]  = None
    status:      str            = "pending"
    tasks:       List[Task]     = []
