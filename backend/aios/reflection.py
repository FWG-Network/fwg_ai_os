"""
backend/aios/reflection.py
Reflection Engine — evaluate goal outcome after execution.
"""
from backend.core.logger import log


class ReflectionEngine:
    """
    Evaluates completed goal by inspecting task results.
    Uses SQLAlchemy GoalModel (from db.py) — not Pydantic Goal.
    """

    def evaluate(self, goal) -> str:
        """
        Analyze task results → return final goal status.

        Returns:
            "completed"          — all tasks succeeded
            "completed_partial"  — some tasks failed but goal achieved
            "failed"             — critical tasks failed
        """
        log.info(f"[Reflection] Evaluating goal id={goal.id} '{goal.description[:60]}'")

        if not goal.tasks:
            log.warning("[Reflection] No tasks found — marking completed")
            return "completed"

        total    = len(goal.tasks)
        failed   = []
        success  = []

        for task in goal.tasks:
            # ✅ Fix: task.result is dict — check status field, not string
            result = task.result or {}

            if isinstance(result, dict):
                has_error = (
                    "error" in result or
                    task.status == "failed"
                )
            else:
                # fallback for string results
                has_error = "failed" in str(result).lower()

            if has_error:
                failed.append(task)
                log.warning(f"[Reflection] Task {task.id} failed: {result}")
            else:
                success.append(task)

        fail_rate = len(failed) / total if total > 0 else 0

        # ── Decision logic ────────────────────────────────────────────
        if fail_rate == 0:
            outcome = "completed"
            log.info(f"[Reflection] ✅ All {total} tasks succeeded → {outcome}")

        elif fail_rate < 0.5:
            outcome = "completed_partial"
            log.warning(
                f"[Reflection] ⚠️ {len(failed)}/{total} tasks failed → {outcome}"
            )

        else:
            outcome = "failed"
            log.error(
                f"[Reflection] ❌ {len(failed)}/{total} tasks failed → {outcome}"
            )

        return outcome


reflection_service = ReflectionEngine()
