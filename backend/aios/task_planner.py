# backend/aios/task_planner.py

from typing import List, Dict, Any
from backend.models.db import Task as TaskModel

class TaskPlanner:
    """
    Upgraded Task Planner that is "intent-aware". It can generate specialized,
    tool-specific plans based on the user's goal.
    """
    def create_plan(self, goal_description: str, goal_id: Any) -> List[List[TaskModel]]:
        """
        Analyzes the goal and creates a staged plan with appropriate tool assignments.
        """
        goal_lower = goal_description.lower()

        # 🚀 TOOL-AGENT UPGRADE: Intent detection
        if "trend" in goal_lower or "emerging creator" in goal_lower or "viral" in goal_lower:
            print("🧠 TaskPlanner: Detected 'Trend Forecasting' intent. Generating specialized plan.")
            return self._create_trend_forecasting_plan(goal_id)
        else:
            print("🧠 TaskPlanner: Detected generic intent. Generating standard research plan.")
            return self._create_generic_research_plan(goal_description, goal_id)

    def _create_trend_forecasting_plan(self, goal_id: Any) -> List[List[TaskModel]]:
        # This specialized plan uses the new trend forecasting tools
        plan = [
            [ # Stage 1: Data Collection (runs in parallel)
                TaskModel(
                    description="Execute a trend investigation scan on YouTube using the theme 'viral trend'.",
                    goal_id=goal_id,
                    tool_name="trend_scanner" # Assign the specific tool
                )
            ],
            [ # Stage 2: Data Analysis
                TaskModel(
                    description="Analyze the collected data to calculate trend velocity and identify emerging creators.",
                    goal_id=goal_id,
                    tool_name="trend_analyzer" # Assign the specific tool
                )
            ],
            [ # Stage 3: Final Synthesis
                TaskModel(
                    description="Synthesize the trend analysis into a final, human-readable briefing report.",
                    goal_id=goal_id,
                    tool_name="llm_agent" # Use the general LLM for the final report
                )
            ]
        ]
        return plan

    def _create_generic_research_plan(self, goal_description: str, goal_id: Any) -> List[List[TaskModel]]:
        # This is the old, generic plan. All tasks use the default llm_agent.
        plan = [
            [ # Stage 1
                TaskModel(description=f"Initial web research for '{goal_description}'", goal_id=goal_id),
                TaskModel(description=f"Internal memory search for related concepts to '{goal_description}'", goal_id=goal_id)
            ],
            [ # Stage 2
                TaskModel(description=f"Synthesize findings for '{goal_description}'", goal_id=goal_id)
            ],
            [ # Stage 3
                TaskModel(description=f"Draft the final summary report for '{goal_description}'", goal_id=goal_id)
            ]
        ]
        return plan

task_planner_service = TaskPlanner()
