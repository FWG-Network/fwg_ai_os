from sqlalchemy.orm import Session
from .task_planner import task_planner_service
from .executor import executor_service
from .reflection import reflection_service
from backend.models.db import Goal as GoalModel, Task as TaskModel

class AutonomousLoop:
    """
    The AutonomousLoop is a stateless orchestration service. It manages the lifecycle
    of a goal by planning, dispatching tasks for intelligent execution, and reflecting
    on the outcome. All state is persisted to a database.
    """

    # ★★★ UPGRADE: Added 'user_id' to the method signature for personalization context ★★★
    def run(self, goal_description: str, user_id: str, db: Session) -> GoalModel:
        """
        The main operating cycle of the AI-OS. This process is persistent, context-aware,
        and triggers real intelligent agents.
        
        Args:
            goal_description: The high-level goal from the user.
            user_id: The ID of the user who initiated the goal, for context.
            db: The SQLAlchemy database session.
            
        Returns:
            The final, completed Goal object from the database.
        """
        print(f"--- 🚀 AUTONOMOUS OS: STARTING GOAL FOR USER '{user_id}': {goal_description} 🚀 ---")
        
        # Goal persistence remains the same
        db_goal = GoalModel(description=goal_description, status="running")
        db.add(db_goal)
        db.commit()
        db.refresh(db_goal)

        # Planning stage remains the same
        print("\n[1. PLANNING STAGE]")
        task_descriptions = task_planner_service.create_plan(goal_description)
        db_tasks = [TaskModel(description=desc, goal_id=db_goal.id) for desc in task_descriptions]
        db.add_all(db_tasks)
        db.commit()
        print(f"Plan created and saved with {len(db_tasks)} tasks.")

        # Execution stage is now context-aware
        print("\n[2. EXECUTION STAGE]")
        for i, task in enumerate(db_tasks):
            print(f"\n--- Processing Task {i+1}/{len(db_tasks)} ---")
            db.refresh(task)
            
            try:
                # ★★★ UPGRADE: Pass the user_id to the executor service ★★★
                # The executor will now dispatch this context to the real AI worker.
                executor_service.execute_task(task, goal_owner_id=user_id)
            except Exception as e:
                print(f"CRITICAL ERROR: Task execution failed for '{task.description}'. Aborting goal.")
                db_goal.status = "failed"
                db.commit()
                raise e
            
            db.commit()

        print("\nExecution of all tasks complete.")

        # Reflection stage remains the same
        print("\n[3. REFLECTION STAGE]")
        db.refresh(db_goal)
        reflection_outcome = reflection_service.evaluate(db_goal)
        db_goal.status = reflection_outcome
        db.commit()
        
        print(f"\n--- ✅ AUTONOMOUS OS: GOAL COMPLETE. FINAL STATUS: {reflection_outcome} ✅ ---")
        return db_goal

# ★★★ UPGRADE: Removed the service instance creation from this file. ★★★
# It is now correctly created in backend/core/services.py
