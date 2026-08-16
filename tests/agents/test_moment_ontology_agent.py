import pytest
import json
from unittest.mock import AsyncMock

from backend.models.schemas import EditorialIntent, MomentOntology
from backend.agents.moment_ontology_agent import MomentOntologyAgent


@pytest.fixture
def mock_llm_router():
    mock = AsyncMock()
    mock.generate.return_value = json.dumps({
        "ontology": [
            {
                "category": "Sports Highlights",
                "moment_types": [
                    {"name": "Goal", "keywords": ["goal", "score"]}
                ],
                "scene_types": [
                    {"name": "Stadium Interior", "visual_cues": ["stands", "pitch"]}
                ]
            }
        ]
    })
    return mock


@pytest.fixture
def editorial_intent_example():
    return EditorialIntent(
        topic="Football Matches",
        niche="Sports Fans",
        creative_brief_summary="Highlights from recent football games.",
        reject_content_types=["interviews"],
        target_emotions=["excitement"]
    )


@pytest.fixture
def agent(mock_llm_router):
    return MomentOntologyAgent(llm_router=mock_llm_router, max_retries=2)


@pytest.mark.asyncio
async def test_generate_moment_ontology_success(agent, mock_llm_router, editorial_intent_example):
    ontology = await agent.generate_moment_ontology(editorial_intent_example)
    mock_llm_router.generate.assert_called_once()
    assert isinstance(ontology, MomentOntology)
    assert ontology.ontology[0].category == "Sports Highlights"


@pytest.mark.asyncio
async def test_generate_moment_ontology_markdown_fence(agent, mock_llm_router, editorial_intent_example):
    mock_llm_router.generate.return_value = "```json\n" + json.dumps({
        "ontology": [{
            "category": "Cooking",
            "moment_types": [{"name": "Chop", "keywords": ["knife", "cut"]}],
            "scene_types": [{"name": "Kitchen", "visual_cues": ["counter"]}]
        }]
    }) + "\n```"
    ontology = await agent.generate_moment_ontology(editorial_intent_example)
    assert ontology.ontology[0].category == "Cooking"


@pytest.mark.asyncio
async def test_generate_moment_ontology_malformed_json_fails(agent, mock_llm_router, editorial_intent_example):
    mock_llm_router.generate.side_effect = ["not json", "still not json"]
    with pytest.raises(ValueError, match="Failed to generate valid MomentOntology"):
        await agent.generate_moment_ontology(editorial_intent_example)
    assert mock_llm_router.generate.call_count == agent.max_retries


@pytest.mark.asyncio
async def test_generate_moment_ontology_retry_feedback(agent, mock_llm_router, editorial_intent_example):
    mock_llm_router.generate.side_effect = [
        "not json",  # attempt 1: invalid JSON must trigger retry
        json.dumps({
            "ontology": [{
                "category": "Music",
                "moment_types": [{"name": "Drop", "keywords": ["beat"]}],
                "scene_types": [{"name": "Stage", "visual_cues": ["lights"]}]
            }]
        })
    ]
    ontology = await agent.generate_moment_ontology(editorial_intent_example)
    assert mock_llm_router.generate.call_count == 2
    assert "Previous attempt failed" in mock_llm_router.generate.call_args_list[1].kwargs['prompt']
    assert ontology.ontology[0].category == "Music"


@pytest.mark.asyncio
async def test_generate_moment_ontology_task_type(agent, mock_llm_router, editorial_intent_example):
    await agent.generate_moment_ontology(editorial_intent_example)
    assert mock_llm_router.generate.call_args.kwargs['task_type'] == "editorial_planning"
    assert mock_llm_router.generate.call_args.kwargs['max_tokens'] == 3000
