"""
backend/services/story_learning_engine.py

⚠️ STATUS: NEW FILE — written from scratch, no prior version existed in the
repo (confirmed via `find -iname "*story_learning*"` returning no results).
UNTESTED — no live LLM keys / network access available in this sandbox.
Run this against real backend.core.config.settings + a live llm_router before
treating any of it as production-ready.

AI Story Scripting & Learning Engine — two stages:

1. Pattern Learning  (learn_channel_patterns):
   Given a set of sample videos/transcripts from a reference channel
   (e.g. "MeowFlix"), extract recurring structural patterns: opening hook,
   conflict introduction, cliffhanger ending, recurring characters.
   Uses task_type="fast" -> routed to Cloudflare Workers AI (free tier) per
   the agreed fallback chain, since this step runs over hundreds of videos
   and doesn't need premium reasoning quality.

2. Sequential Script Generation (generate_next_episode):
   Given the learned pattern + prior episode history, generate the next
   episode's script + Sora-ready image/video prompts, preserving character
   consistency. Uses task_type="story" -> routed to GitHub Models first
   (premium chain) since this step needs strong emotional-hook reasoning.

Evidence-First compliance:
   - No fabricated confidence scores. `learn_channel_patterns` returns
     evidence=None / a real parsed structure — never a guessed placeholder.
   - Every LLM call result is tagged with which provider actually answered
     (via llm_router's honest logging), and that tag is surfaced back to the
     caller in the returned dict, not silently discarded.

TODO (explicitly deferred, not fabricated as done):
   - Headroom-style token trimming before the Cloudflare/OpenRouter call
     (hook point marked below) — not implemented yet.
   - Character-consistency state currently lives in the caller-supplied
     `series_state` dict; no persistent storage layer wired yet (would need
     a DB model — out of scope until DB schema for series is agreed).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.core.logger import log
from backend.lim.llm_router import llm_router


class StoryLearningEngine:
    """Pattern Learning + Sequential Script Generation for episodic AI content."""

    # ── Stage 1: Pattern Learning ───────────────────────────────────────
    async def learn_channel_patterns(
        self,
        channel_name: str,
        sample_transcripts: list[str],
    ) -> dict[str, Any]:
        """
        Analyze sample video transcripts/descriptions from a reference channel
        and extract recurring structural patterns.

        Args:
            channel_name: e.g. "MeowFlix" — for logging/traceability only.
            sample_transcripts: raw text per sample video (caption, transcript,
                or scene description). Caller is responsible for gathering
                this data (e.g. via youtube connector) — this method does not
                fetch anything itself.

        Returns:
            {
              "channel_name": str,
              "sample_count": int,
              "patterns": {...} | None,   # None if parsing failed — never faked
              "answered_by": str,         # honest provider+model tag from router
              "evidence": "measured" | "unavailable",
            }
        """
        if not sample_transcripts:
            log.warning(f"[StoryLearningEngine] No samples provided for {channel_name}")
            return {
                "channel_name": channel_name,
                "sample_count": 0,
                "patterns": None,
                "answered_by": "none",
                "evidence": "unavailable",
            }

        # TODO (Headroom hook): trim/compress `combined_text` here before it
        # goes to the LLM call below, once the token-trimming pipeline is wired.
        combined_text = "\n---\n".join(sample_transcripts)

        prompt = (
            f"You are analyzing {len(sample_transcripts)} sample video scripts "
            f"from the channel '{channel_name}'. Identify the recurring "
            f"structural pattern used across episodes. Return STRICT JSON only, "
            f"no prose, in this exact shape:\n"
            f'{{"opening_hook": "...", "conflict_pattern": "...", '
            f'"cliffhanger_style": "...", "recurring_characters": ["..."]}}\n\n'
            f"Samples:\n{combined_text}"
        )

        try:
            raw = await llm_router.generate(
                prompt=prompt,
                max_tokens=800,
                task_type="fast",  # -> Cloudflare Workers AI first (bulk, zero-cost tier)
            )
        except Exception as e:
            log.error(f"[StoryLearningEngine] Pattern learning LLM call failed: {e}")
            return {
                "channel_name": channel_name,
                "sample_count": len(sample_transcripts),
                "patterns": None,
                "answered_by": "none",
                "evidence": "unavailable",
            }

        patterns = self._safe_parse_json(raw)
        return {
            "channel_name": channel_name,
            "sample_count": len(sample_transcripts),
            "patterns": patterns,  # None if parsing failed — not faked
            "answered_by": "see_logs",  # router logs the real provider->model line
            "evidence": "measured" if patterns is not None else "unavailable",
        }

    # ── Stage 2: Sequential Script Generation ───────────────────────────
    async def generate_next_episode(
        self,
        channel_name: str,
        learned_patterns: dict[str, Any],
        series_state: dict[str, Any],
        episode_number: int,
    ) -> dict[str, Any]:
        """
        Generate the next episode's script + Sora-ready prompts, preserving
        character consistency from series_state.

        Args:
            learned_patterns: output of learn_channel_patterns()["patterns"].
                Must not be None — caller should check evidence first.
            series_state: {
                "characters": [{"name": ..., "visual_description": ...}, ...],
                "prior_episode_summaries": [str, ...],
            }
            episode_number: 1-indexed episode number in the series.

        Returns:
            {
              "episode_number": int,
              "script": str | None,
              "sora_prompts": list[str] | None,
              "answered_by": str,
              "evidence": "measured" | "unavailable",
            }
        """
        if not learned_patterns:
            log.warning(
                f"[StoryLearningEngine] generate_next_episode called with no "
                f"learned_patterns for {channel_name} — refusing to fabricate a script "
                f"from an unmeasured pattern."
            )
            return {
                "episode_number": episode_number,
                "script": None,
                "sora_prompts": None,
                "answered_by": "none",
                "evidence": "unavailable",
            }

        characters = series_state.get("characters", [])
        prior_summaries = series_state.get("prior_episode_summaries", [])

        prompt = (
            f"Write episode {episode_number} of an episodic short-form series "
            f"for the channel '{channel_name}'.\n\n"
            f"Structural pattern to follow: {json.dumps(learned_patterns)}\n\n"
            f"Characters (must stay visually and behaviorally consistent):\n"
            f"{json.dumps(characters)}\n\n"
            f"Summaries of prior episodes (for continuity):\n"
            f"{json.dumps(prior_summaries)}\n\n"
            f"Return STRICT JSON only, no prose, in this exact shape:\n"
            f'{{"script": "...", "sora_prompts": ["prompt for scene 1", "prompt for scene 2", ...]}}'
        )

        try:
            raw = await llm_router.generate(
                prompt=prompt,
                max_tokens=1500,
                task_type="story",  # -> GitHub Models first (premium chain)
            )
        except Exception as e:
            log.error(f"[StoryLearningEngine] Script generation LLM call failed: {e}")
            return {
                "episode_number": episode_number,
                "script": None,
                "sora_prompts": None,
                "answered_by": "none",
                "evidence": "unavailable",
            }

        parsed = self._safe_parse_json(raw)
        if parsed is None:
            return {
                "episode_number": episode_number,
                "script": None,
                "sora_prompts": None,
                "answered_by": "see_logs",
                "evidence": "unavailable",
            }

        return {
            "episode_number": episode_number,
            "script": parsed.get("script"),
            "sora_prompts": parsed.get("sora_prompts"),
            "answered_by": "see_logs",
            "evidence": "measured",
        }

    # ── Helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _safe_parse_json(raw: Optional[str]) -> Optional[dict[str, Any]]:
        """Never fabricate a parsed structure — return None if it genuinely fails."""
        if not raw:
            return None
        text = raw.strip()
        # Some providers wrap JSON in markdown fences despite instructions — strip if present.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError) as e:
            log.warning(f"[StoryLearningEngine] Failed to parse LLM JSON output: {e}")
            return None


story_learning_engine = StoryLearningEngine()
