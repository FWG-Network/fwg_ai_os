from sqlalchemy.orm import Session
from .task_planner import task_planner_service
from .executor import executor_service
from .reflection import reflection_service

# ★★★ FIX: Import the SQLAlchemy database models and session, not the Pydantic schemas ★★★
from backend.models.db import Goal as GoalModel, Task as TaskModel

class AutonomousLoop:
    """
    The AutonomousLoop is a stateless orchestration service. It manages the lifecycle
    of a goal by planning, dispatching tasks for execution, and reflecting on the
    outcome. All state is persisted to a database.
    """

    def run(self, goal_description: str, db: Session) -> GoalModel:
        """
        The main operating cycle of the AI-OS. This process is now persistent and resumable.
        
        Args:
            goal_description: The high-level goal from the user.
            db: The SQLAlchemy database session.
            
        Returns:
            The final, completed Goal object from the database.
        """
        print(f"--- 🚀 AUTONOMOUS OS: STARTING GOAL: {goal_description} 🚀 ---")
        
        # ★★★ FIX: Persist the initial Goal to the PostgreSQL database ★★★
        # This makes the goal durable and survives restarts.
        db_goal = GoalModel(description=goal_description, status="running")
        db.add(db_goal)
        db.commit()
        db.refresh(db_goal)

        # 1. Plan: Create a set of task descriptions.
        print("\n[1. PLANNING STAGE]")
        task_descriptions = task_planner_service.create_plan(goal_description)
        
        # ★★★ FIX: Persist the planned tasks to the database ★★★
        db_tasks = [TaskModel(description=desc, goal_id=db_goal.id) for desc in task_descriptions]
        db.add_all(db_tasks)
        db.commit()
        print(f"Plan created and saved with {len(db_tasks)} tasks.")

        # 2. Execute: Dispatch each task and update its state in the DB.
        print("\n[2. EXECUTION STAGE]")
        for i, task in enumerate(db_tasks):
            print(f"\n--- Processing Task {i+1}/{len(db_tasks)} ---")
            db.refresh(task) # Ensure we have the latest state before execution
            
            try:
                # The executor now dispatches to Celery and waits. It will update
                # the task object's status and result internally.
                executor_service.execute_task(task)
            except Exception as e:
                # If the task execution fails after retries, we mark the whole goal as failed.
                print(f"CRITICAL ERROR: Task execution failed for '{task.description}'. Aborting goal.")
                db_goal.status = "failed"
                db.commit()
                raise e # Re-raise the exception to the API layer
            
            # ★★★ FIX: Commit the updated task state (status, result) to the DB ★★★
            db.commit()

        print("\nExecution of all tasks complete.")

        # 3. Reflect: Evaluate the final outcome of the persisted goal.
        print("\n[3. REFLECTION STAGE]")
        db.refresh(db_goal) # Refresh the goal to get all updated task results
        reflection_outcome = reflection_service.evaluate(db_goal)
        
        db_goal.status = reflection_outcome
        db.commit()
        
        print(f"\n--- ✅ AUTONOMOUS OS: GOAL COMPLETE. FINAL STATUS: {reflection_outcome} ✅ ---")
        return db_goal

# Create a single, reusable instance of the service
autonomous_loop_service = AutonomousLoop()
