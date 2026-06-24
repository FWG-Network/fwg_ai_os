from .goal import Task
from .agent import Agent

class Executor:
    def execute_task(self, task: Task, agent: Agent) -> str:
        """Executes a single task using a specified agent."""
        task.status = "running"
        result = agent.run(task.description)
        task.result = result
        task.status = "completed"
        return result
