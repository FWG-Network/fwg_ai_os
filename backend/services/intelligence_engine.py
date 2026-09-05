"""
Evidence-backed candidate intelligence layer.

Position:
    Discovery / SourceHunter -> Intelligence -> Evaluation -> Ranking

Rules:
- Never fabricate missing platform metrics.
- Preserve the original candidate payload.
- Novelty / rarity / competition remain unavailable until a comparison corpus exists.
- Keep the existing RankingEngine contract by projecting editorial relevance to
  `semantic_score`.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import math
import re
from collections.abc import Mapping
from typing import Any


_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


class IntelligenceEngine:
    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        if value is None:
            return {}

        if isinstance(value, Mapping):
            return dict(value)

        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return dict(model_dump())

        return {}

    @staticmethod
    def _tokens(*values: Any) -> set[str]:
        parts: list[str] = []

        for value in values:
            if value is None:
                continue

            if isinstance(value, (list, tuple, set)):
                parts.extend(str(item) for item in value)
            else:
                parts.append(str(value))

        return {
            token.lower()
            for part in parts
            for token in _TOKEN_RE.findall(part)
        }

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))

    def _editorial_relevance(
        self,
        candidate: Mapping[str, Any],
        editorial_intent: Any = None,
        moment_ontology: Any = None,
    ) -> tuple[float, list[str]]:
        intent = self._as_dict(editorial_intent)
        ontology = self._as_dict(moment_ontology)

        candidate_tokens = self._tokens(
            candidate.get("title"),
            candidate.get("tags", []),
            candidate.get("description"),
        )

        topic_tokens = self._tokens(
            intent.get("topic"),
            intent.get("niche"),
        )

        emotion_tokens = self._tokens(
            intent.get("target_emotions", []),
        )

        ontology_tokens: set[str] = set()

        for category in ontology.get("ontology", []) or []:
            category_data = self._as_dict(category)

            ontology_tokens |= self._tokens(
                category_data.get("category"),
                category_data.get("description"),
            )

            for moment in category_data.get("moment_types", []) or []:
                moment_data = self._as_dict(moment)

                ontology_tokens |= self._tokens(
                    moment_data.get("name"),
                    moment_data.get("description"),
                )

                for scene in moment_data.get("scene_types", []) or []:
                    scene_data = self._as_dict(scene)

                    ontology_tokens |= self._tokens(
                        scene_data.get("name"),
                        scene_data.get("description"),
                        scene_data.get("visual_cues", []),
                    )

        topic_overlap = (
            len(candidate_tokens & topic_tokens)
            / max(len(topic_tokens), 1)
        )

        ontology_overlap = (
            len(candidate_tokens & ontology_tokens)
            / max(len(ontology_tokens), 1)
        )

        emotion_overlap = (
            len(candidate_tokens & emotion_tokens)
            / max(len(emotion_tokens), 1)
        )

        if ontology_tokens:
            score = (
                0.55 * topic_overlap
                + 0.35 * ontology_overlap
                + 0.10 * emotion_overlap
            )
        else:
            score = (
                0.80 * topic_overlap
                + 0.20 * emotion_overlap
            )

        evidence: list[str] = []

        if topic_overlap > 0:
            evidence.append("topic/niche token overlap")

        if ontology_overlap > 0:
            evidence.append("moment ontology token overlap")

        if emotion_overlap > 0:
            evidence.append("target emotion token overlap")

        if not evidence:
            evidence.append(
                "no semantic overlap found in available metadata"
            )

        return self._clamp(score), evidence

    def _viral_potential(
        self,
        candidate: Mapping[str, Any],
    ) -> tuple[float, list[str]]:
        views = candidate.get("views")
        likes = candidate.get("likes")
        engagement = candidate.get("engagement_rate")

        components: list[float] = []
        evidence: list[str] = []

        if isinstance(views, (int, float)) and views >= 0:
            popularity = min(
                math.log10(float(views) + 1.0) / 8.0,
                1.0,
            )
            components.append(popularity)
            evidence.append("observed views")

        if isinstance(engagement, (int, float)) and engagement >= 0:
            components.append(
                self._clamp(float(engagement))
            )
            evidence.append("observed engagement_rate")

        elif (
            isinstance(likes, (int, float))
            and isinstance(views, (int, float))
            and views > 0
        ):
            components.append(
                self._clamp(float(likes) / float(views))
            )
            evidence.append("observed likes/views ratio")

        published_at = candidate.get("published_at")

        if published_at:
            try:
                published = datetime.fromisoformat(
                    str(published_at).replace("Z", "+00:00")
                )

                if published.tzinfo is None:
                    published = published.replace(
                        tzinfo=timezone.utc
                    )

                age_days = max(
                    (
                        datetime.now(timezone.utc) - published
                    ).total_seconds()
                    / 86400.0,
                    0.0,
                )

                freshness = max(
                    0.0,
                    1.0 - age_days / 365.0,
                )

                components.append(freshness)
                evidence.append("published_at freshness")

            except (TypeError, ValueError, OverflowError):
                evidence.append(
                    "published_at present but not parseable"
                )

        if not components:
            return (
                0.0,
                ["no observed traction or freshness metrics"],
            )

        return (
            self._clamp(
                sum(components) / len(components)
            ),
            evidence,
        )

    def _content_quality(
        self,
        candidate: Mapping[str, Any],
    ) -> tuple[float, list[str]]:
        checks = {
            "non-empty id": bool(candidate.get("id")),
            "non-empty url": bool(candidate.get("url")),
            "non-empty title": bool(candidate.get("title")),
            "platform identified": bool(candidate.get("platform")),
        }

        score = sum(checks.values()) / len(checks)

        evidence = [
            name
            for name, ok in checks.items()
            if ok
        ]

        return score, evidence

    def _evidence_confidence(
        self,
        candidate: Mapping[str, Any],
    ) -> tuple[float, list[str]]:
        checks = [
            bool(candidate.get("id")),
            bool(candidate.get("url")),
            bool(candidate.get("title")),
            bool(candidate.get("platform")),
            isinstance(
                candidate.get("observed_metrics"),
                Mapping,
            ),
            bool(candidate.get("_provenance")),
        ]

        score = sum(checks) / len(checks)

        evidence = [
            "source identity present"
            if checks[0]
            else "source identity missing",

            "source URL present"
            if checks[1]
            else "source URL missing",

            "title present"
            if checks[2]
            else "title missing",

            "platform present"
            if checks[3]
            else "platform missing",

            "observed_metrics container present"
            if checks[4]
            else "observed_metrics unavailable",

            "provenance attached"
            if checks[5]
            else "provenance unavailable",
        ]

        return score, evidence

    def analyze_candidate(
        self,
        candidate: Mapping[str, Any],
        *,
        editorial_intent: Any = None,
        moment_ontology: Any = None,
    ) -> dict[str, Any]:
        relevance, relevance_evidence = self._editorial_relevance(
            candidate,
            editorial_intent,
            moment_ontology,
        )

        viral, viral_evidence = self._viral_potential(candidate)

        quality, quality_evidence = self._content_quality(
            candidate
        )

        confidence, confidence_evidence = (
            self._evidence_confidence(candidate)
        )

        intelligence = {
            "editorial_relevance": round(relevance, 6),
            "novelty": None,
            "viral_potential": round(viral, 6),
            "content_quality": round(quality, 6),
            "rarity": None,
            "competition": None,
            "evidence_confidence": round(confidence, 6),
            "evidence": {
                "editorial_relevance": relevance_evidence,
                "viral_potential": viral_evidence,
                "content_quality": quality_evidence,
                "evidence_confidence": confidence_evidence,
                "novelty": [
                    "comparison corpus not supplied"
                ],
                "rarity": [
                    "comparison corpus not supplied"
                ],
                "competition": [
                    "comparison corpus not supplied"
                ],
            },
        }

        enriched = dict(candidate)

        # Backward-compatible bridge into current RankingEngine.
        enriched["semantic_score"] = (
            intelligence["editorial_relevance"]
        )

        enriched["intelligence"] = intelligence

        return enriched

    def analyze(
        self,
        candidates: list[Mapping[str, Any]],
        *,
        provenance: Mapping[
            str,
            list[dict[str, Any]],
        ] | None = None,
        editorial_intent: Any = None,
        moment_ontology: Any = None,
    ) -> list[dict[str, Any]]:
        provenance = provenance or {}

        analyzed: list[dict[str, Any]] = []

        for candidate in candidates:
            item = dict(candidate)

            clip_id = str(
                item.get("id", "")
            )

            item["_provenance"] = list(
                provenance.get(
                    clip_id,
                    item.get("_provenance", []),
                )
            )

            analyzed.append(
                self.analyze_candidate(
                    item,
                    editorial_intent=editorial_intent,
                    moment_ontology=moment_ontology,
                )
            )

        return analyzed


intelligence_engine_service = IntelligenceEngine()
