import json
from pydantic import ValidationError
from typing import Any, Optional
import logging
import asyncio

from backend.models.schemas import EditorialIntent, MomentOntology, DiscoveryMission


class DiscoveryStrategyPlannerAgent:
    def __init__(self, llm_router: Any, max_retries: int = 3, logger: Optional[logging.Logger] = None):
        self.llm_router = llm_router
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)

    def _normalize_mission(self, mission: DiscoveryMission) -> DiscoveryMission:
        for strategy in mission.platform_strategies:
            strategy.primary_queries = strategy.primary_queries or []
            strategy.secondary_queries = strategy.secondary_queries or []
            strategy.hashtags = strategy.hashtags or []
            strategy.keywords = strategy.keywords or []
            if not strategy.primary_queries and not strategy.keywords:
                self.logger.warning(
                    f"Empty primary_queries AND keywords for platform {strategy.platform} "
                    f"in mission '{mission.mission_focus}' — LLM output may be insufficient."
                )
        return mission

    async def plan_discovery_strategy(
        self, editorial_intent: EditorialIntent, moment_ontology: MomentOntology
    ) -> list[DiscoveryMission]:
        system_prompt = (
            "You are an expert AI Discovery Strategy Planner. Generate concrete, "
            "executable discovery missions with platform-specific search strategies. "
            "You MUST derive primary_queries and keywords ONLY from the specific "
            "moment types, scene types, and visual cues provided in the MomentOntology "
            "— never restate the topic generically.\n\n"
            "CRITICAL: NEVER use terms like 'compilation', 'best of', 'top 10', "
            "'viral videos', 'amazing videos', 'funny moments'. Focus on raw, "
            "event-driven, specific visual content (e.g. 'POV helmet cam freefall', "
            "not 'best skydiving clips'). Ensure primary_queries and keywords are "
            "non-empty for each platform strategy."
        )

        json_schema_hint = f"""
JSON Schema for a list of DiscoveryMission objects:
{json.dumps(DiscoveryMission.model_json_schema(), indent=2)}

Generate the JSON output strictly as a JSON array, inside a markdown code fence (```json ... ```).
"""

        current_user_prompt = (
            f"Editorial Intent:\n{editorial_intent.model_dump_json(indent=2)}\n\n"
            f"Moment Ontology:\n{moment_ontology.model_dump_json(indent=2)}"
        )
        last_error_feedback = ""

        for attempt in range(self.max_retries):
            self.logger.info(f"Attempt {attempt + 1}/{self.max_retries} to plan DiscoveryStrategy.")

            full_prompt = f"{system_prompt}\n{json_schema_hint}\n{current_user_prompt}"
            if attempt > 0 and last_error_feedback:
                full_prompt += f"\n\nPrevious attempt failed with this error. Fix and retry:\n{last_error_feedback}"

            json_str = ""
            raw_llm_output = ""
            try:
                raw_llm_output = await self.llm_router.generate(
                    prompt=full_prompt,
                    max_tokens=6000,
                    task_type="editorial_planning"
                )

                if "```json" in raw_llm_output:
                    json_str = raw_llm_output.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = raw_llm_output.strip()

                parsed_json = json.loads(json_str)
                missions = [DiscoveryMission(**item) for item in parsed_json]
                missions = [self._normalize_mission(m) for m in missions]

                self.logger.info("DiscoveryStrategy planned and validated successfully.")
                return missions

            except json.JSONDecodeError as e:
                last_error_feedback = f"JSON decoding failed: {e}. Raw output: {raw_llm_output[:500]}"
                self.logger.warning(f"JSON decoding failed (attempt {attempt + 1}): {e}")
            except ValidationError as e:
                last_error_feedback = f"Pydantic validation failed: {e}. Raw JSON: {json_str[:500]}"
                self.logger.warning(f"Validation failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                last_error_feedback = f"Unexpected error: {e}. Raw output: {raw_llm_output[:500]}"
                self.logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")

            await asyncio.sleep(1)

        self.logger.error(f"Failed to generate valid DiscoveryStrategy after {self.max_retries} attempts.")
        raise ValueError("Failed to generate valid DiscoveryStrategy after multiple retries.")
