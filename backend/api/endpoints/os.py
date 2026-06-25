# backend/api/endpoints/os.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.models.db import get_db, Goal as GoalModel
from backend.aios.autonomous_loop import autonomous_loop_service

class OSRequest(BaseModel):
    goal_description: str
    user_id: str = "default_user"

router = APIRouter()

@router.post("/run", response_model_exclude_none=True)
async def run_autonomous_goal(request: OSRequest, db: Session = Depends(get_db)):
    """
    Starts the Autonomous Operating System with a high-level goal and user context.
    """
    completed_goal = autonomous_loop_service.run(
        goal_desc=request.goal_description,
        user_id=request.user_id,
        db=db
    )
    # A full representation of the complex SQLAlchemy object might be too verbose
    # or cause circular reference issues in FastAPI's JSON rendering.
    # We return a summary instead.
    return {
        "goal_id": completed_goal.id,
        "description": completed_goal.description,
        "final_status": completed_goal.status,
        "task_count": len(completed_goal.tasks),
        "final_summary": completed_goal.tasks[-1].result if completed_goal.tasks else "N/A"
    }
