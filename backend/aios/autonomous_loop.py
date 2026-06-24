from .goal import Goal
from .task_planner import TaskPlanner
from .reflection import ReflectionEngine
from .executor import Executor
from .agent import Agent, MockLLMAgent

class AutonomousLoop:
    def __init__(self):
        self.planner = TaskPlanner()
        self.executor = Executor()
        self.reflection = ReflectionEngine()
        # The OS selects an agent. For now, it's our mock LLM agent.
        self.agent = MockLLMAgent() 

    def run(self, goal: Goal):
        """The main operating cycle of the AI-OS."""
        print(f"--- 🚀 AUTONOMOUS OS: STARTING GOAL: {goal.description} 🚀 ---")
        goal.status = "running"

        # 1. Plan: Create a set of tasks from the high-level goal.
        print("\n[1. PLANNING STAGE]")
        tasks = self.planner.create_plan(goal)
        goal.tasks = tasks
        print(f"Plan created with {len(tasks)} tasks.")

        # 2. Execute: Run each task in sequence.
        print("\n[2. EXECUTION STAGE]")
        for i, task in enumerate(goal.tasks):
            print(f"\n--- Executing Task {i+1}/{len(goal.tasks)} ---")
            self.executor.execute_task(task, self.agent)
        print("\nExecution of all tasks complete.")

        # 3. Reflect: Evaluate the final outcome.
        print("\n[3. REFLECTION STAGE]")
        reflection_outcome = self.reflection.evaluate(goal)
        
        goal.status = "completed"
        print(f"\n--- ✅ AUTONOMOUS OS: GOAL COMPLETE. FINAL STATUS: {reflection_outcome} ✅ ---")
        return goal
