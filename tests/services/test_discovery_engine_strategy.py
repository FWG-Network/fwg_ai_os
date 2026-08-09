import pytest
from unittest.mock import AsyncMock, patch

from backend.services.discovery_engine import DiscoveryEngine


@pytest.fixture
def engine():
    e = DiscoveryEngine()
    e._redis_client = False  # force cache-skip path, no real Redis needed
    return e


@pytest.mark.asyncio
async def test_discover_from_strategy_forwards_all_filters(engine):
    with patch("backend.services.discovery_engine.youtube_connector") as mock_connector:
        mock_connector.search = AsyncMock(return_value=[])
        filters = {
            "min_views": 500,
            "days_ago_start": 30,
            "days_ago_end": 0,
            "region_code": "US",
            "relevance_language": "en",
        }
        await engine.discover_from_strategy("test query", filters)

        mock_connector.search.assert_called_once()
        call_kwargs = mock_connector.search.call_args.kwargs
        assert call_kwargs["min_views"] == 500
        assert call_kwargs["days_ago_start"] == 30
        assert call_kwargs["days_ago_end"] == 0
        assert call_kwargs["region_code"] == "US"
        assert call_kwargs["relevance_language"] == "en"
        assert call_kwargs["exclude_reposts"] is True


@pytest.mark.asyncio
async def test_discover_from_strategy_partial_filters_only_forwards_present_keys(engine):
    with patch("backend.services.discovery_engine.youtube_connector") as mock_connector:
        mock_connector.search = AsyncMock(return_value=[])
        await engine.discover_from_strategy("test query", {"min_views": 100})

        call_kwargs = mock_connector.search.call_args.kwargs
        assert call_kwargs["min_views"] == 100
        assert "days_ago_start" not in call_kwargs
        assert "region_code" not in call_kwargs


@pytest.mark.asyncio
async def test_discover_from_strategy_empty_filters_uses_connector_defaults(engine):
    with patch("backend.services.discovery_engine.youtube_connector") as mock_connector:
        mock_connector.search = AsyncMock(return_value=[])
        await engine.discover_from_strategy("test query", {})

        call_kwargs = mock_connector.search.call_args.kwargs
        assert call_kwargs["min_views"] == 0
        assert call_kwargs["exclude_reposts"] is True
        assert "days_ago_start" not in call_kwargs
