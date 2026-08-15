from backend.aios.task_planner import task_planner_service
from backend.models.db import Task as TaskModel


def test_task_planner_creates_a_plan():
    """Tests if the TaskPlanner generates a staged plan of TaskModel objects."""
    goal_description = "Test Goal"
    staged_plan = task_planner_service.create_plan(goal_description, goal_id=1)

    assert isinstance(staged_plan, list)
    assert len(staged_plan) > 0
    assert all(isinstance(stage, list) for stage in staged_plan)

    flat = [task for stage in staged_plan for task in stage]
    assert len(flat) > 0
    assert all(isinstance(task, TaskModel) for task in flat)
