import logging
from typing import Optional

from backend.models.schemas import DiscoveryMission, PlatformStrategy, RawClip, SourceHunterResult

SUPPORTED_PLATFORMS = {"youtube", "tiktok"}

# Fields YouTubeConnector.search() actually accepts, mapped from mission
# filter dict keys. Anything not listed here is UNSUPPORTED and must be
# warned about explicitly, never silently dropped or treated as applied.
_LANGUAGE_MAP = {
    "english": "en",
    "khmer": "km",
    "spanish": "es",
    "french": "fr",
}

_UPLOAD_DATE_TO_DAYS = {
    "last_24_hours": 1,
    "last_7_days": 7,
    "last_30_days": 30,
    "last_year": 365,
}


class SourceHunterAgent:
    """
    Orchestrates execution of DiscoveryMission[] against real platform
    connectors, via DiscoveryEngine.discover_from_strategy(). Owns
    validation, query resolution, and mission-filter -> connector-param
    translation. Does NOT implement its own YouTube client, cache, or
    dedup — reuses DiscoveryEngine's existing infrastructure.
    """

    def __init__(self, discovery_engine, logger: Optional[logging.Logger] = None):
        self.discovery_engine = discovery_engine
        self.logger = logger or logging.getLogger(__name__)

    def _resolve_queries(self, strategy: PlatformStrategy) -> list[str]:
        """
        primary_queries -> fallback to keywords -> [] if both empty.
        Each entry is executed as an INDEPENDENT search (never concatenated
        into a single mega-query). Never fabricates a query from
        mission_focus or adds generic modifiers.
        """
        primary = strategy.primary_queries or []
        if primary:
            return list(primary)

        keywords = strategy.keywords or []
        if keywords:
            return list(keywords)

        return []

    def _translate_filters(self, filters: dict, mission_focus: str, platform: str) -> dict:
        """
        Translate mission-level filter dict into YouTubeConnector.search()'s
        actual accepted params. Unsupported fields produce an explicit
        warning and are dropped (never silently "applied").
        """
        translated: dict = {}
        recognized_keys = {"min_views", "language", "upload_date"}

        for key, value in filters.items():
            if key == "min_views":
                try:
                    translated["min_views"] = int(value)
                except (TypeError, ValueError):
                    self.logger.warning(
                        f"[SourceHunterAgent] Ignoring invalid min_views value "
                        f"'{value}' for mission '{mission_focus}' on '{platform}'."
                    )

            elif key == "language":
                lang_code = _LANGUAGE_MAP.get(str(value).strip().lower())
                if lang_code:
                    translated["relevance_language"] = lang_code
                else:
                    self.logger.warning(
                        f"[SourceHunterAgent] Unrecognized language filter "
                        f"'{value}' for mission '{mission_focus}' on '{platform}' "
                        f"— not applied."
                    )

            elif key == "upload_date":
                days = _UPLOAD_DATE_TO_DAYS.get(str(value).strip().lower())
                if days is not None:
                    translated["days_ago_start"] = days
                else:
                    self.logger.warning(
                        f"[SourceHunterAgent] Unrecognized upload_date filter "
                        f"'{value}' for mission '{mission_focus}' on '{platform}' "
                        f"— not applied."
                    )

            if key not in recognized_keys:
                self.logger.warning(
                    f"[SourceHunterAgent] Filter '{key}'={value!r} for mission "
                    f"'{mission_focus}' on '{platform}' is NOT supported by "
                    f"YouTubeConnector and will NOT be applied."
                )

        return translated

    def _map_to_raw_clip(self, item: dict, platform: str) -> RawClip:
        return RawClip(
            id=item.get("id", ""),
            url=item.get("url", ""),
            title=item.get("title", ""),
            platform=item.get("platform", platform),
            channel=item.get("channel"),
            tags=item.get("tags", []),
            views=item.get("views", 0),
            likes=item.get("likes", 0),
            engagement_rate=item.get("engagement_rate", 0),
            published_at=item.get("published_at"),
            observed_metrics=item.get("observed_metrics", {}),
            metric_schema_version=item.get("metric_schema_version"),
        )

    async def hunt(self, missions: list[DiscoveryMission]) -> SourceHunterResult:
        all_clips: list[RawClip] = []
        seen_ids: set[str] = set()
        provenance: dict[str, list[dict]] = {}

        for mission in missions:
            for strategy in mission.platform_strategies:
                platform = strategy.platform.strip().lower()

                if platform not in SUPPORTED_PLATFORMS:
                    self.logger.warning(
                        f"[SourceHunterAgent] Skipping unsupported platform "
                        f"'{strategy.platform}' for mission '{mission.mission_focus}' "
                        f"— no connector implemented yet."
                    )
                    continue

                queries = self._resolve_queries(strategy)
                if not queries:
                    self.logger.warning(
                        f"[SourceHunterAgent] Skipping strategy for platform "
                        f"'{strategy.platform}' in mission '{mission.mission_focus}' "
                        f"— both primary_queries and keywords are empty."
                    )
                    continue

                translated_filters = self._translate_filters(
                    strategy.filters or {}, mission.mission_focus, platform
                )

                for query in queries:
                    try:
                        results = await self.discovery_engine.discover_from_strategy(
                            query, translated_filters, platform=platform
                        )
                    except Exception as e:
                        self.logger.error(
                            f"[SourceHunterAgent] discover_from_strategy failed for "
                            f"query '{query}' on '{platform}': {e}"
                        )
                        continue

                    for item in results:
                        clip = self._map_to_raw_clip(item, platform)
                        if not clip.id:
                            continue
                        record = {"query": query, "platform": platform, "mission_focus": mission.mission_focus}
                        provenance.setdefault(clip.id, []).append(record)
                        if clip.id not in seen_ids:
                            seen_ids.add(clip.id)
                            all_clips.append(clip)

        self.logger.info(f"[SourceHunterAgent] hunt complete: {len(all_clips)} unique clips")
        return SourceHunterResult(clips=all_clips, provenance=provenance)
