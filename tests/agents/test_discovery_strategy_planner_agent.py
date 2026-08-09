import pytest
import json
from unittest.mock import AsyncMock

from backend.models.schemas import (
    EditorialIntent, MomentOntology, MomentType, SceneType,
    MomentOntologyCategory, DiscoveryMission, PlatformStrategy,
)
from backend.agents.discovery_strategy_planner_agent import DiscoveryStrategyPlannerAgent


def make_editorial_intent():
    return EditorialIntent(
        topic="Raw skydiving freefall footage",
        niche="Extreme sports / adrenaline content",
        creative_brief_summary="Authentic, unedited skydiving freefall clips with handheld camera feel",
        desired_clip_characteristics={"style": "raw", "editing": "none"},
        reject_content_types=["compilations", "viral edits"],
        target_emotions=["adrenaline", "authentic"],
    )


def make_moment_ontology():
    return MomentOntology(
        ontology=[
            MomentOntologyCategory(
                category="Freefall Moments",
                moment_types=[
                    MomentType(name="Freefall", keywords=["freefall", "descent"]),
                    MomentType(name="High-Speed Descent", keywords=["speed", "wind"]),
                ],
                scene_types=[
                    SceneType(name="Wide-Angle Sky", visual_cues=["wind noise", "handheld shake"]),
                ],
            )
        ]
    )


def valid_mission_json():
    return [
        {
            "mission_focus": "Specific moments of skydiving freefall",
            "clip_criteria": {"style": "raw"},
            "priority_score": 90,
            "confidence_score": 85,
            "estimated_cost": "Low",
            "expected_yield": "High",
            "platform_strategies": [
                {
                    "platform": "YouTube",
                    "search_approach": "Event-specific",
                    "primary_queries": ["skydiving freefall helmet cam", "raw parachute deployment footage"],
                    "secondary_queries": ["skydiving wind noise raw"],
                    "hashtags": ["#skydiving", "#freefall"],
                    "keywords": ["handheld camera", "no CGI"],
                    "filters": {"upload_date": "last_year"},
                }
            ],
        }
    ]


@pytest.fixture
def mock_llm_router():
    mock = AsyncMock()
    mock.generate.return_value = json.dumps(valid_mission_json())
    return mock


@pytest.fixture
def agent(mock_llm_router):
    return DiscoveryStrategyPlannerAgent(llm_router=mock_llm_router, max_retries=2)


@pytest.mark.asyncio
async def test_plan_discovery_strategy_success(agent, mock_llm_router):
    missions = await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    mock_llm_router.generate.assert_called_once()
    assert isinstance(missions, list)
    assert isinstance(missions[0], DiscoveryMission)
    assert missions[0].mission_focus == "Specific moments of skydiving freefall"
    assert "skydiving freefall helmet cam" in missions[0].platform_strategies[0].primary_queries


@pytest.mark.asyncio
async def test_plan_discovery_strategy_markdown_fence(agent, mock_llm_router):
    mock_llm_router.generate.return_value = "```json\n" + json.dumps(valid_mission_json()) + "\n```"
    missions = await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    assert missions[0].mission_focus == "Specific moments of skydiving freefall"


@pytest.mark.asyncio
async def test_plan_discovery_strategy_malformed_json_fails(agent, mock_llm_router):
    mock_llm_router.generate.side_effect = ["not json", "still not json"]
    with pytest.raises(ValueError, match="Failed to generate valid DiscoveryStrategy"):
        await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    assert mock_llm_router.generate.call_count == agent.max_retries


@pytest.mark.asyncio
async def test_plan_discovery_strategy_retry_feedback(agent, mock_llm_router):
    bad = valid_mission_json()
    del bad[0]["priority_score"]
    mock_llm_router.generate.side_effect = [json.dumps(bad), json.dumps(valid_mission_json())]
    missions = await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    assert mock_llm_router.generate.call_count == 2
    assert "Previous attempt failed" in mock_llm_router.generate.call_args_list[1].kwargs['prompt']
    assert missions[0].priority_score == 90


@pytest.mark.asyncio
async def test_plan_discovery_strategy_normalization_null_queries(agent, mock_llm_router):
    data = valid_mission_json()
    data[0]["platform_strategies"][0]["primary_queries"] = None
    data[0]["platform_strategies"][0]["hashtags"] = None
    mock_llm_router.generate.return_value = json.dumps(data)
    missions = await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    strategy = missions[0].platform_strategies[0]
    assert strategy.primary_queries == []
    assert strategy.hashtags == []
    assert strategy.keywords == ["handheld camera", "no CGI"]


@pytest.mark.asyncio
async def test_plan_discovery_strategy_task_type_and_tokens(agent, mock_llm_router):
    await agent.plan_discovery_strategy(make_editorial_intent(), make_moment_ontology())
    assert mock_llm_router.generate.call_args.kwargs['task_type'] == "editorial_planning"
    assert mock_llm_router.generate.call_args.kwargs['max_tokens'] == 6000
