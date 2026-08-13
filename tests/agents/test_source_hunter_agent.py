import pytest
from unittest.mock import AsyncMock

from backend.models.schemas import DiscoveryMission, PlatformStrategy, RawClip
from backend.agents.source_hunter_agent import SourceHunterAgent


def make_mission(platform="youtube", primary_queries=None, keywords=None, filters=None):
    return DiscoveryMission(
        mission_focus="Test mission",
        clip_criteria={},
        priority_score=80,
        confidence_score=80,
        estimated_cost="Low",
        expected_yield="High",
        platform_strategies=[
            PlatformStrategy(
                platform=platform,
                search_approach="Event-specific",
                primary_queries=primary_queries,
                secondary_queries=[],
                hashtags=[],
                keywords=keywords,
                filters=filters or {},
            )
        ],
    )


@pytest.fixture
def mock_discovery_engine():
    mock = AsyncMock()
    mock.discover_from_strategy.return_value = [
        {"id": "abc123", "url": "https://youtube.com/watch?v=abc123", "title": "Test Clip",
         "platform": "youtube", "channel": "TestChannel", "tags": ["raw"], "views": 1000,
         "likes": 50, "engagement_rate": 0.05, "published_at": "2026-01-01T00:00:00Z"}
    ]
    return mock


@pytest.fixture
def agent(mock_discovery_engine):
    return SourceHunterAgent(discovery_engine=mock_discovery_engine)


@pytest.mark.asyncio
async def test_valid_youtube_strategy(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=["raw skydiving footage"])
    result = await agent.hunt([mission])
    mock_discovery_engine.discover_from_strategy.assert_called_once()
    assert len(result.clips) == 1
    assert isinstance(result.clips[0], RawClip)
    assert result.clips[0].id == "abc123"


@pytest.mark.asyncio
async def test_primary_queries_used_over_keywords(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=["raw footage"], keywords=["should not be used"])
    await agent.hunt([mission])
    call_args = mock_discovery_engine.discover_from_strategy.call_args
    assert call_args[0][0] == "raw footage"


@pytest.mark.asyncio
async def test_multiple_primary_queries_each_executed_independently(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=["query one", "query two", "query three"])
    await agent.hunt([mission])
    assert mock_discovery_engine.discover_from_strategy.call_count == 3
    called_queries = [c[0][0] for c in mock_discovery_engine.discover_from_strategy.call_args_list]
    assert called_queries == ["query one", "query two", "query three"]
    # never concatenated into one mega-query
    assert "query one query two" not in called_queries


@pytest.mark.asyncio
async def test_one_failed_query_does_not_abort_remaining(agent, mock_discovery_engine):
    async def side_effect(query, filters, platform=None):
        if query == "bad query":
            raise Exception("simulated failure")
        return [{"id": f"clip-{query}", "url": "u", "title": "t", "platform": "youtube"}]

    mock_discovery_engine.discover_from_strategy.side_effect = side_effect
    mission = make_mission(primary_queries=["bad query", "good query"])
    result = await agent.hunt([mission])
    assert mock_discovery_engine.discover_from_strategy.call_count == 2
    assert len(result.clips) == 1
    assert result.clips[0].id == "clip-good query"


@pytest.mark.asyncio
async def test_keywords_fallback_when_primary_empty(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=[], keywords=["handheld", "raw"])
    await agent.hunt([mission])
    assert mock_discovery_engine.discover_from_strategy.call_count == 2
    called_queries = [c[0][0] for c in mock_discovery_engine.discover_from_strategy.call_args_list]
    assert called_queries == ["handheld", "raw"]


@pytest.mark.asyncio
async def test_empty_primary_and_keywords_skips_strategy(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=[], keywords=[])
    result = await agent.hunt([mission])
    mock_discovery_engine.discover_from_strategy.assert_not_called()
    assert result.clips == []


@pytest.mark.asyncio
async def test_unsupported_platform_warning_skip(agent, mock_discovery_engine, caplog):
    mission = make_mission(platform="reddit", primary_queries=["test"])
    result = await agent.hunt([mission])
    mock_discovery_engine.discover_from_strategy.assert_not_called()
    assert result.clips == []
    assert "unsupported platform" in caplog.text.lower()


@pytest.mark.asyncio
async def test_raw_clip_mapping_fields(agent):
    mission = make_mission(primary_queries=["test query"])
    result = await agent.hunt([mission])
    clip = result.clips[0]
    assert clip.title == "Test Clip"
    assert clip.channel == "TestChannel"
    assert clip.views == 1000
    assert clip.tags == ["raw"]


@pytest.mark.asyncio
async def test_connector_failure_does_not_crash(agent, mock_discovery_engine):
    mock_discovery_engine.discover_from_strategy.side_effect = Exception("API down")
    mission = make_mission(primary_queries=["test"])
    result = await agent.hunt([mission])
    assert result.clips == []


@pytest.mark.asyncio
async def test_dedup_across_missions(agent, mock_discovery_engine):
    mission1 = make_mission(primary_queries=["query one"])
    mission2 = make_mission(primary_queries=["query two"])
    result = await agent.hunt([mission1, mission2])
    # same mocked clip id "abc123" returned every call -> deduped to 1
    assert len(result.clips) == 1
    assert len(result.provenance["abc123"]) == 2


@pytest.mark.asyncio
async def test_dedup_across_multiple_queries_same_strategy(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=["query a", "query b", "query c"])
    result = await agent.hunt([mission])
    # mock returns clip id "abc123" for every query -> deduped to 1
    assert len(result.clips) == 1
    assert len(result.provenance["abc123"]) == 3
    assert mock_discovery_engine.discover_from_strategy.call_count == 3

@pytest.mark.asyncio
async def test_provenance_record_shape(agent, mock_discovery_engine):
    mission = make_mission(primary_queries=["query one"])
    result = await agent.hunt([mission])
    records = result.provenance["abc123"]
    assert len(records) == 1
    record = records[0]
    assert set(record.keys()) == {"query", "platform", "mission_focus"}
    assert record["query"] == "query one"
    assert record["platform"] == "youtube"
    assert record["mission_focus"] == mission.mission_focus


@pytest.mark.asyncio
async def test_filter_translation_min_views_and_language(agent, mock_discovery_engine):
    mission = make_mission(
        primary_queries=["test"],
        filters={"min_views": "500", "language": "English", "upload_date": "last_30_days"},
    )
    await agent.hunt([mission])
    call_args = mock_discovery_engine.discover_from_strategy.call_args
    translated = call_args[0][1]
    assert translated["min_views"] == 500
    assert translated["relevance_language"] == "en"
    assert translated["days_ago_start"] == 30


@pytest.mark.asyncio
async def test_filter_translation_unsupported_field_warns(agent, mock_discovery_engine, caplog):
    mission = make_mission(primary_queries=["test"], filters={"duration_min": "30"})
    await agent.hunt([mission])
    call_args = mock_discovery_engine.discover_from_strategy.call_args
    translated = call_args[0][1]
    assert "duration_min" not in translated
    assert "not supported" in caplog.text.lower()
