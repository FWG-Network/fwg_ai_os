from backend.aios.task_planner import task_planner_service

def test_task_planner_creates_a_plan():
    """
    Tests if the TaskPlanner generates a list of tasks for a given goal.
    """
    goal_description = "Test Goal"
    plan = task_planner_service.create_plan(goal_description)
    
    # Assert that a plan is a list and is not empty
    assert isinstance(plan, list)
    assert len(plan) > 0
    
    # Assert that the goal description is included in the plan steps
    assert all(goal_description in task_desc for task_desc in plan)

def test_plan_structure():
    """
    Tests that the generated plan has a logical structure (e.g., starts with research, ends with summary).
    """
    goal_description = "Analyze user engagement"
    plan = task_planner_service.create_plan(goal_description)
    
    assert "research" in plan[0].lower()
    assert "summary" in plan[-1].lower() or "conclusion" in plan[-1].lower()
