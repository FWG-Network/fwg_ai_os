from backend.aios.task_planner import TaskPlanner


def _plan(goal: str):
    planner = TaskPlanner()
    return planner.create_plan(goal, goal_id=123)


def _tools(plan):
    return [
        (task.tool_name, task.tool_params)
        for stage in plan
        for task in stage
    ]


def test_generation_routes_only_to_writer_llm():
    plan = _plan("Generate a simple article about AI")

    assert _tools(plan) == [
        ("llm_agent", {"task_type": "writer"}),
    ]


def test_memory_search_routes_only_to_vector_memory():
    plan = _plan("Search memory for our previous creator research")

    assert _tools(plan) == [
        ("vector_memory", None),
    ]


def test_trend_research_routes_to_trend_pipeline():
    plan = _plan("Research emerging creator trends")

    tools = _tools(plan)

    assert [tool for tool, _ in tools] == [
        "trend_scanner",
        "trend_analyzer",
        "llm_agent",
    ]


def test_exact_output_has_priority_over_generation():
    plan = _plan("Write a reply with exactly: FWG_OK")

    tools = _tools(plan)

    assert tools == [
        ("llm_agent", {"task_type": "exact"}),
    ]


def test_generic_research_keeps_research_pipeline():
    plan = _plan("Research the latest creator economy trends")

    tools = _tools(plan)

    assert [tool for tool, _ in tools] == [
        "trend_scanner",
        "trend_analyzer",
        "llm_agent",
    ]
