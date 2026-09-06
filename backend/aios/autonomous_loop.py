"""
backend/aios/autonomous_loop.py
Autonomous OS Loop — Plan → Execute (staged) → Reflect.
"""
import asyncio
from typing import Dict, Any, Optional
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

    ✅ Result propagation: Stage N output -> Stage N+1 input via execution_key/input_from.
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

        execution_key_registry: Dict[str, TaskModel] = {}

        try:
            for stage_idx, stage_tasks in enumerate(staged_plan):
                log.info(
                    f"[AIOS] Stage {stage_idx + 1}/{len(staged_plan)}: "
                    f"{len(stage_tasks)} tasks"
                )

                resolved_inputs_map = self._resolve_stage_dependencies(
                    stage_tasks,
                    execution_key_registry,
                    db,
                )

                # ✅ Fix 3: async execute_task_group (parallel within stage)
                await executor_service.execute_task_group(
                    tasks=stage_tasks,
                    db=db,
                    user_id=user_id,    # ✅ pass user_id for personalization
                    execution_context=resolved_inputs_map,
                )
                db.commit()

                if any(task.status == "failed" for task in stage_tasks):
                    log.warning(
                        f"[AIOS] Stage {stage_idx + 1} failed; "
                        "stopping later stage execution"
                    )
                    break

                for task in stage_tasks:
                    task_params = task.tool_params or {}
                    if "execution_key" in task_params:
                        key = task_params["execution_key"]
                        if key in execution_key_registry and execution_key_registry[key].id != task.id:
                            log.error(f"[AIOS] Duplicate execution_key '{key}' in goal {db_goal.id}")
                            raise ValueError(f"Duplicate execution_key: {key}")
                        execution_key_registry[key] = task

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

    # ── Dependency Resolution ────────────────────────────────────────
    def _resolve_stage_dependencies(
        self,
        stage_tasks: list,
        execution_key_registry: Dict[str, TaskModel],
        db: Session,
    ) -> Dict[int, Optional[Dict[str, Any]]]:
        """
        ✅ NEW: Resolve input_from dependencies for tasks in this stage.

        Returns: {task.id: {input_name: resolved_value}} for dependent tasks.
        """
        resolved_inputs = {}

        for task in stage_tasks:
            task_params = task.tool_params or {}
            input_from = task_params.get("input_from")

            if not input_from:
                # Task has no dependencies; skip
                continue

            log.info(f"[AIOS] Task {task.id} declares dependency: {input_from}")

            if not isinstance(input_from, dict):
                task.status = "failed"
                task.result = {
                    "error": "dependency_result_malformed",
                    "dependency": "",
                    "expected_path": "",
                }
                db.add(task)
                log.error(
                    f"[AIOS] Task {task.id} has malformed dependency: "
                    f"input_from must be an object, got {type(input_from).__name__}"
                )
                continue

            dependency_key = input_from.get("execution_key")
            result_path = input_from.get("result_path")
            input_name = input_from.get("input_name")

            # Validate dependency structure
            if not all(
                isinstance(value, str) and value
                for value in (dependency_key, result_path, input_name)
            ):
                task.status = "failed"
                task.result = {
                    "error": "dependency_result_malformed",
                    "dependency": dependency_key or "",
                    "expected_path": result_path or "",
                }
                db.add(task)
                log.error(f"[AIOS] Task {task.id} has malformed dependency: {input_from}")
                continue

            # Find producer task
            producer = execution_key_registry.get(dependency_key)
            if not producer:
                task.status = "failed"
                task.result = {"error": "dependency_not_found", "dependency": dependency_key}
                db.add(task)
                log.error(f"[AIOS] Task {task.id} dependency not found: {dependency_key}")
                continue

            # Verify producer completed
            if producer.status != "completed":
                task.status = "failed"
                task.result = {"error": "dependency_failed", "dependency": dependency_key}
                db.add(task)
                log.error(f"[AIOS] Task {task.id} producer failed: {dependency_key} status={producer.status}")
                continue

            # Verify producer has result
            if producer.result is None:
                task.status = "failed"
                task.result = {"error": "dependency_result_missing", "dependency": dependency_key}
                db.add(task)
                log.error(f"[AIOS] Task {task.id} producer result missing: {dependency_key}")
                continue

            # Resolve result_path
            resolved_value = self._extract_result_path(
                producer.result,
                result_path,
            )
            if resolved_value is _MISSING:
                task.status = "failed"
                task.result = {
                    "error": "dependency_result_malformed",
                    "dependency": dependency_key,
                    "expected_path": result_path,
                }
                db.add(task)
                log.error(f"[AIOS] Task {task.id} result path not found: {result_path} in {producer.result}")
                continue

            # ✅ Success: store resolved input
            if task.id not in resolved_inputs:
                resolved_inputs[task.id] = {}
            resolved_inputs[task.id][input_name] = resolved_value
            log.info(f"[AIOS] Task {task.id} resolved {input_name} from {dependency_key}.{result_path}")

        return resolved_inputs

    @staticmethod
    def _extract_result_path(result: Any, path: str) -> Any:
        """
        ✅ NEW: Extract nested value from result using dot notation.

        Example: "videos" -> result["videos"]
        Example: "metadata.title" -> result["metadata"]["title"]
        """
        keys = path.split(".")
        current = result

        for key in keys:
            if isinstance(current, dict):
                if key not in current:
                    return _MISSING
                current = current[key]
            elif isinstance(current, list) and key.isdigit():
                index = int(key)
                if index >= len(current):
                    return _MISSING
                current = current[index]
            else:
                return _MISSING

        return current


# ── Global instance ───────────────────────────────────────────────────
autonomous_loop_service = AutonomousLoop()


_MISSING = object()
