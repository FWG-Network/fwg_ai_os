from .goal import Task
from backend.aios.tasks import execute_agent_task # Will create this task

class Executor:
    def execute_task(self, task: Task) -> str:
        print(f"Dispatching task '{task.description}' to Celery worker...")
        task.status = "dispatched"
        
        # Send task to Celery and wait for the result
        async_result = execute_agent_task.delay(task.description)
        
        try:
            # Wait for up to 5 minutes
            result = async_result.get(timeout=300)
            task.result = result
            task.status = "completed"
            print(f"Task '{task.description}' completed by worker.")
            return result
        except Exception as e:
            task.result = f"ERROR: {str(e)}"
            task.status = "failed"
            print(f"ERROR: Task '{task.description}' failed. Error: {e}")
            raise e

executor_service = Executor()
