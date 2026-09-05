from backend.services.intelligence_engine import (
    IntelligenceEngine,
)
from backend.services.evaluation_engine import (
    EvaluationEngine,
)


def test_intelligence_preserves_candidate_and_provenance():
    intelligence = IntelligenceEngine()

    candidate = {
        "id": "yt-1",
        "url": "https://example.com/1",
        "title": "Funny dog jumps over car",
        "platform": "youtube",
        "tags": ["funny", "dog"],
        "views": 10000,
        "likes": 1000,
        "observed_metrics": {
            "views": 10000,
            "likes": 1000,
        },
    }

    result = intelligence.analyze(
        [candidate],
        provenance={
            "yt-1": [
                {
                    "query": "funny dog",
                    "platform": "youtube",
                }
            ]
        },
        editorial_intent={
            "topic": "dog",
            "niche": "funny animals",
            "target_emotions": ["funny"],
        },
    )

    assert len(result) == 1
    assert result[0]["id"] == "yt-1"
    assert result[0]["url"] == candidate["url"]
    assert result[0]["_provenance"][0]["query"] == "funny dog"
    assert "intelligence" in result[0]
    assert result[0]["semantic_score"] == (
        result[0]["intelligence"]["editorial_relevance"]
    )


def test_intelligence_does_not_fabricate_comparison_scores():
    intelligence = IntelligenceEngine()

    result = intelligence.analyze(
        [
            {
                "id": "1",
                "url": "https://example.com",
                "title": "dog",
                "platform": "youtube",
                "observed_metrics": {},
            }
        ]
    )

    item = result[0]["intelligence"]

    assert item["novelty"] is None
    assert item["rarity"] is None
    assert item["competition"] is None


def test_intelligence_preserves_discovery_provenance_without_override():
    intelligence = IntelligenceEngine()

    result = intelligence.analyze(
        [
            {
                "id": "tiktok-1",
                "url": "https://example.com/tiktok-1",
                "title": "AI video trend",
                "platform": "tiktok",
                "observed_metrics": {},
                "_provenance": [
                    {
                        "query": "AI video trends",
                        "platform": "tiktok",
                    }
                ],
            }
        ],
        editorial_intent={"topic": "AI video trends"},
    )

    assert result[0]["_provenance"] == [
        {
            "query": "AI video trends",
            "platform": "tiktok",
        }
    ]


def test_ranking_handles_missing_platform_metrics_without_fabrication():
    from backend.services.ranking_engine import RankingEngine

    ranked = RankingEngine().rank(
        [
            {
                "id": "tiktok-1",
                "platform": "tiktok",
                "semantic_score": 0.5,
                "views": None,
                "likes": None,
                "age_days": None,
            }
        ]
    )

    assert len(ranked) == 1
    assert ranked[0]["_score_debug"]["popularity"] == 0.0
    assert ranked[0]["_score_debug"]["engagement"] == 0.0
    assert ranked[0]["_score_debug"]["freshness"] == 0.0


def test_intelligence_is_deterministic_for_static_candidate():
    intelligence = IntelligenceEngine()

    candidate = {
        "id": "1",
        "url": "https://example.com",
        "title": "dog funny",
        "platform": "youtube",
        "tags": ["dog", "funny"],
        "views": 1000,
        "likes": 100,
        "observed_metrics": {},
    }

    kwargs = {
        "editorial_intent": {
            "topic": "dog",
            "niche": "animals",
            "target_emotions": ["funny"],
        }
    }

    first = intelligence.analyze([candidate], **kwargs)
    second = intelligence.analyze([candidate], **kwargs)

    assert first[0]["intelligence"] == second[0]["intelligence"]


def test_evaluation_creates_explicit_decision():
    intelligence = IntelligenceEngine()
    evaluation = EvaluationEngine()

    candidates = intelligence.analyze(
        [
            {
                "id": "1",
                "url": "https://example.com",
                "title": "dog funny",
                "platform": "youtube",
                "tags": ["dog", "funny"],
                "views": 10000,
                "likes": 1000,
                "observed_metrics": {},
            }
        ],
        provenance={
            "1": [{"query": "dog funny"}]
        },
        editorial_intent={
            "topic": "dog",
            "niche": "animals",
            "target_emotions": ["funny"],
        },
    )

    result = evaluation.evaluate(candidates)

    assert len(result) == 1
    assert result[0]["evaluation"]["decision"] in {
        "accept",
        "reject",
    }
    assert "reason" in result[0]["evaluation"]
    assert "weaknesses" in result[0]["evaluation"]


def test_evaluation_rejects_low_evidence_candidate():
    evaluation = EvaluationEngine()

    result = evaluation.evaluate(
        [
            {
                "id": "1",
                "url": "",
                "title": "",
                "platform": "",
                "intelligence": {
                    "editorial_relevance": 0.0,
                    "evidence_confidence": 0.0,
                    "evidence": {},
                },
            }
        ]
    )

    assert result[0]["evaluation"]["decision"] == "reject"
    assert result[0]["evaluation"]["weaknesses"]
