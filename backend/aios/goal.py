from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

class Task(BaseModel):
    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4()}")
    description: str
    status: str = "pending"
    result: Optional[str] = None

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4()}")
    description: str
    status: str = "pending"
    tasks: List[Task] = []
