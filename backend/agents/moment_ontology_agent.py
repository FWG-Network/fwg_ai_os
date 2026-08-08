import json
from pydantic import ValidationError
from typing import Any, Optional
import logging
import asyncio

from backend.models.schemas import EditorialIntent, MomentOntology


class MomentOntologyAgent:
    def __init__(self, llm_router: Any, max_retries: int = 3, logger: Optional[logging.Logger] = None):
        self.llm_router = llm_router
        self.max_retries = max_retries
        self.logger = logger or logging.getLogger(__name__)

    async def generate_moment_ontology(self, editorial_intent: EditorialIntent) -> MomentOntology:
        system_prompt = (
            "You are an expert AI assistant specialized in expanding editorial intents "
            "into detailed, visualizable moment ontologies. Expand the editorial intent "
            "into specific Moment Types and associated Scene Types (visualizable scenarios) "
            "relevant to the content's topic and niche. Your output must be a valid JSON "
            "object adhering strictly to the provided schema."
        )

        json_schema_hint = f"""
JSON Schema for MomentOntology:
{json.dumps(MomentOntology.model_json_schema(), indent=2)}

Generate the JSON output strictly inside a markdown code fence (```json ... ```).
"""

        current_user_prompt = f"Editorial Intent:\n{editorial_intent.model_dump_json(indent=2)}"
        last_error_feedback = ""

        for attempt in range(self.max_retries):
            self.logger.info(f"Attempt {attempt + 1}/{self.max_retries} to generate MomentOntology.")

            full_prompt = f"{system_prompt}\n{json_schema_hint}\n{current_user_prompt}"
            if attempt > 0 and last_error_feedback:
                full_prompt += f"\n\nPrevious attempt failed with this error. Fix and retry:\n{last_error_feedback}"

            json_str = ""
            raw_llm_output = ""
            try:
                raw_llm_output = await self.llm_router.generate(
                    prompt=full_prompt,
                    max_tokens=3000,
                    task_type="editorial_planning"
                )

                if "```json" in raw_llm_output:
                    json_str = raw_llm_output.split("```json")[1].split("```")[0].strip()
                else:
                    json_str = raw_llm_output.strip()

                parsed_json = json.loads(json_str)
                moment_ontology = MomentOntology(**parsed_json)
                self.logger.info("MomentOntology generated and validated successfully.")
                return moment_ontology

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

        self.logger.error(f"Failed to generate valid MomentOntology after {self.max_retries} attempts.")
        raise ValueError("Failed to generate valid MomentOntology after multiple retries.")
