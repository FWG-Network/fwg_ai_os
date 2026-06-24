from .goal import Goal

class ReflectionEngine:
    def evaluate(self, goal: Goal) -> str:
        """Evaluates the outcome of a completed goal."""
        # A real reflection engine would analyze the results vs the initial goal.
        # It could use an LLM to check for quality, correctness, and alignment.
        print(f"Reflecting on goal '{goal.description}'...")
        
        for task in goal.tasks:
            if "failed" in (task.result or ""):
                print("Reflection: Found a failed task. Suggesting improvement.")
                return "IMPROVEMENT_NEEDED"

        print("Reflection: All tasks successful. Goal achieved.")
        return "SUCCESS"
