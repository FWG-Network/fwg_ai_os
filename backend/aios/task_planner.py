from .goal import Goal, Task

class TaskPlanner:
    def create_plan(self, goal: Goal) -> List[Task]:
        """Breaks a high-level goal into a sequence of actionable tasks."""
        # In a real system, this could be a complex call to a planning-focused LLM.
        # Here, we simulate a simple breakdown.
        plan = [
            Task(description=f"Initial research and context gathering for '{goal.description}'"),
            Task(description=f"Execute core logic to address '{goal.description}'"),
            Task(description=f"Review and verify the result for '{goal.description}'"),
            Task(description=f"Final summarization of the outcome for '{goal.description}'")
        ]
        return plan
