# backend/aios/executor.py

from .goal import Task
# Import the real Celery task signature
from backend.aios.tasks import execute_agent_task

class Executor:
    """
    The Executor is now a pure dispatcher. It sends tasks to the Celery
    worker system for remote, asynchronous execution and waits for the result.
    """
    def execute_task(self, task: Task, goal_owner_id: str) -> str:
        print(f"Dispatching task '{task.description}' to Celery worker...")
        task.status = "dispatched"
        
        # Dispatch the real task to the Celery queue and wait for it to complete.
        # We pass the user_id for context in the LLM brain.
        async_result = execute_agent_task.delay(task_description=task.description, user_id=goal_owner_id)
        
        try:
            # Wait for result with a 5-minute timeout
            result = async_result.get(timeout=300) 
            task.result = result
            task.status = "completed"
            print(f"Task '{task.description}' completed by worker.")
            return result
        except Exception as e:
            task.result = f"ERROR: {str(e)}"
            task.status = "failed"
            print(f"ERROR: Task '{task.description}' failed in worker. Error: {e}")
            raise e

executor_service = Executor()
