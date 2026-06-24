# ★★★ FIX: Import the service instance directly ★★★
from backend.aios.task_planner import task_planner_service

def test_task_planner_creates_a_plan():
    """Tests if the TaskPlanner generates a list of task descriptions."""
    goal_description = "Test Goal"
    plan = task_planner_service.create_plan(goal_description)
    
    assert isinstance(plan, list)
    assert len(plan) > 0
    # ★★★ FIX: Check for string type, not Task object ★★★
    assert all(isinstance(task_desc, str) for task_desc in plan)
