from backend.aios.task_planner import task_planner_service

def test_task_planner_creates_a_plan():
    """Tests if the TaskPlanner generates a list of task descriptions for a given goal."""
    goal_description = "Test Goal for Planning"
    plan = task_planner_service.create_plan(goal_description)
    
    assert isinstance(plan, list)
    assert len(plan) > 0
    assert all(isinstance(task_desc, str) for task_desc in plan)
    assert all(goal_description in task_desc for task_desc in plan)
