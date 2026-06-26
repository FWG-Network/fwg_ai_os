# backend/aios/task_planner.py
from typing import List, Any
from backend.models.db import Task as TaskModel
from backend.core.logger import log

# ─── Intent keyword groups ───────────────────────────────────────────
_TREND_KEYWORDS = {"trend", "emerging creator", "viral"}   # ✅ ចាស់: broad


class TaskPlanner:
    """
    Intent-aware Task Planner.
    Detects goal type and generates a staged, tool-assigned execution plan.
    """

    def create_plan(
        self, goal_description: str, goal_id: Any
    ) -> List[List[TaskModel]]:
        goal_lower = goal_description.lower()

        if any(kw in goal_lower for kw in _TREND_KEYWORDS):
            log.info(f"[TaskPlanner] Intent=TrendForecasting  goal_id={goal_id}")
            return self._create_trend_forecasting_plan(goal_id, goal_lower)

        log.info(f"[TaskPlanner] Intent=GenericResearch  goal_id={goal_id}")
        return self._create_generic_research_plan(goal_description, goal_id)

    # ─── Trend Forecasting Plan ──────────────────────────────────────
    def _create_trend_forecasting_plan(
        self, goal_id: Any, goal_lower: str = ""
    ) -> List[List[TaskModel]]:

        # ✅ ថ្មី: tool_params ដើម្បី executor ដឹងថា scan អ្វី
        keyword = self._extract_trend_keyword(goal_lower)

        return [
            [   # Stage 1 — Data Collection
                TaskModel(
                    description=f"Trend scan on YouTube for '{keyword}'.",
                    goal_id=goal_id,
                    tool_name="trend_scanner",
                    tool_params={"theme_keyword": keyword},   # ✅ ថ្មី
                )
            ],
            [   # Stage 2 — Analysis
                TaskModel(
                    description="Calculate trend velocity and identify emerging creators.",
                    goal_id=goal_id,
                    tool_name="trend_analyzer",
                )
            ],
            [   # Stage 3 — Synthesis
                TaskModel(
                    description="Synthesize trend analysis into a human-readable briefing.",
                    goal_id=goal_id,
                    tool_name="llm_agent",
                )
            ],
        ]

    # ─── Generic Research Plan ───────────────────────────────────────
    def _create_generic_research_plan(
        self, goal_description: str, goal_id: Any
    ) -> List[List[TaskModel]]:

        return [
            [   # Stage 1 — Parallel data gathering ✅ ចាស់
                TaskModel(
                    description=f"Web research for '{goal_description}'.",
                    goal_id=goal_id,
                    tool_name="web_search",
                ),
                TaskModel(
                    description=f"Vector memory search for '{goal_description}'.",
                    goal_id=goal_id,
                    tool_name="vector_memory",   # ✅ explicit tool
                ),
            ],
            [   # Stage 2 — Synthesize
                TaskModel(
                    description=f"Synthesize findings for '{goal_description}'.",
                    goal_id=goal_id,
                    tool_name="llm_agent",
                )
            ],
            [   # Stage 3 — Report
                TaskModel(
                    description=f"Draft final summary report for '{goal_description}'.",
                    goal_id=goal_id,
                    tool_name="llm_agent",
                )
            ],
        ]

    # ─── Helpers ─────────────────────────────────────────────────────
    @staticmethod
    def _extract_trend_keyword(goal_lower: str) -> str:
        """Pull a meaningful keyword from the goal, fallback to 'viral trend'."""
        for phrase in ("emerging creator", "viral topic", "viral"):
            if phrase in goal_lower:
                return phrase
        return "viral trend"


task_planner_service = TaskPlanner()
