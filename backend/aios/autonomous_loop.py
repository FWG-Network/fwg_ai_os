"""
backend/aios/autonomous_loop.py
Autonomous OS Loop — Plan → Execute (staged) → Reflect.
"""
import asyncio
from sqlalchemy.orm import Session

from backend.models.db import Goal as GoalModel, Task as TaskModel
from backend.core.logger import log


class AutonomousLoop:
    """
    Stateless orchestration of the AIOS goal lifecycle.
    All state persisted to DB.

    Stages (from task_planner):
      Stage 1: Data collection (parallel)
      Stage 2: Analysis
      Stage 3: Synthesis/Report
    """

    async def run(
        self,
        goal_description: str,
        user_id:          str,
        db:               Session,
    ) -> GoalModel:
        """
        Main AIOS cycle:
        1. Persist goal
        2. Plan (staged task list)
        3. Execute each stage (parallel within stage)
        4. Reflect and finalize
        """
        log.info(f"[AIOS] 🚀 Starting goal for user='{user_id}': '{goal_description}'")

        # ── Persist Goal ──────────────────────────────────────────────
        db_goal = GoalModel(
            description=goal_description,
            user_id=user_id,
            status="running",
        )
        db.add(db_goal)
        db.commit()
        db.refresh(db_goal)
        log.info(f"[AIOS] Goal persisted id={db_goal.id}")

        # ── Plan ─────────────────────────────────────────────────────
        log.info(f"[AIOS] [1/3] PLANNING...")
        from backend.aios.task_planner import task_planner_service

        # ✅ Fix 1: pass goal_id (2nd arg)
        # ✅ Fix 2: returns List[List[TaskModel]] — staged!
        staged_plan: list = task_planner_service.create_plan(
            goal_description,
            db_goal.id,
        )

        # Persist all tasks to DB
        all_tasks = []
        for stage_idx, stage_tasks in enumerate(staged_plan):
            for task in stage_tasks:
                task.goal_id = db_goal.id
                db.add(task)
                all_tasks.append(task)

        db.commit()
        log.info(
            f"[AIOS] Plan: {len(staged_plan)} stages, "
            f"{len(all_tasks)} tasks total"
        )

        # ── Execute (stage by stage) ──────────────────────────────────
        log.info(f"[AIOS] [2/3] EXECUTING...")
        from backend.aios.executor import executor_service

        try:
            for stage_idx, stage_tasks in enumerate(staged_plan):
                log.info(
                    f"[AIOS] Stage {stage_idx + 1}/{len(staged_plan)}: "
                    f"{len(stage_tasks)} tasks"
                )
                # ✅ Fix 3: async execute_task_group (parallel within stage)
                await executor_service.execute_task_group(
                    tasks=stage_tasks,
                    db=db,
                    user_id=user_id,    # ✅ pass user_id for personalization
                )
                db.commit()
                log.info(f"[AIOS] Stage {stage_idx + 1} complete ✅")

        except Exception as e:
            log.error(f"[AIOS] Execution failed: {e}")
            db_goal.status = "failed"
            db.commit()
            raise

        # ── Reflect ───────────────────────────────────────────────────
        log.info(f"[AIOS] [3/3] REFLECTING...")
        db.refresh(db_goal)

        try:
            from backend.aios.reflection import reflection_service
            outcome = reflection_service.evaluate(db_goal)
        except Exception as e:
            log.warning(f"[AIOS] Reflection failed: {e} → defaulting to completed")
            outcome = "completed"

        db_goal.status = outcome
        db.commit()

        log.info(f"[AIOS] ✅ Goal complete. status={outcome}")
        return db_goal


# ── Global instance ───────────────────────────────────────────────────
autonomous_loop_service = AutonomousLoop()
