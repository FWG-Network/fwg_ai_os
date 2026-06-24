# ★★★ FIX: Import 'List' and return the correct, simple type ★★★
from typing import List

class TaskPlanner:
    def create_plan(self, goal_description: str) -> List[str]:
        """Breaks a high-level goal into a sequence of actionable task descriptions."""
        plan_descriptions = [
            f"Initial research for '{goal_description}'",
            f"Execute core logic for '{goal_description}'",
            f"Review and verify result for '{goal_description}'",
            f"Final summary for '{goal_description}'"
        ]
        return plan_descriptions

task_planner_service = TaskPlanner()
