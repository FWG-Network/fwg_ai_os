"""
Deterministic candidate evaluation layer.

Consumes IntelligenceEngine output and produces explicit editorial
acceptance/evaluation evidence without inventing facts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class EvaluationEngine:
    MIN_RELEVANCE = 0.20
    MIN_CONFIDENCE = 0.50

    def evaluate_candidate(
        self,
        candidate: Mapping[str, Any],
    ) -> dict[str, Any]:
        item = dict(candidate)

        intelligence = item.get("intelligence")

        if not isinstance(intelligence, Mapping):
            intelligence = {}

        relevance = float(
            intelligence.get(
                "editorial_relevance",
                0.0,
            )
            or 0.0
        )

        confidence = float(
            intelligence.get(
                "evidence_confidence",
                0.0,
            )
            or 0.0
        )

        weaknesses: list[str] = []

        if relevance < self.MIN_RELEVANCE:
            weaknesses.append(
                "weak editorial relevance"
            )

        if confidence < self.MIN_CONFIDENCE:
            weaknesses.append(
                "insufficient source evidence"
            )

        acceptance = (
            "reject"
            if weaknesses
            else "accept"
        )

        evaluation = {
            "decision": acceptance,
            "editorial_match": relevance,
            "evidence_confidence": confidence,
            "strengths": list(
                intelligence.get("evidence", {})
                .get("editorial_relevance", [])
                if isinstance(
                    intelligence.get("evidence"),
                    Mapping,
                )
                else []
            ),
            "weaknesses": weaknesses,
            "reason": (
                "; ".join(weaknesses)
                if weaknesses
                else "candidate meets current deterministic evaluation thresholds"
            ),
        }

        item["evaluation"] = evaluation

        return item

    def evaluate(
        self,
        candidates: list[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            self.evaluate_candidate(candidate)
            for candidate in candidates
        ]


evaluation_engine_service = EvaluationEngine()
