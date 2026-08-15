from backend.services.ranking_engine import ranking_engine_service


def test_ranking_engine_sorts_by_score():
    """Tests if the ranking engine correctly sorts candidates by their final score."""
    candidates = [
        {"id": "A", "views": 100, "likes": 1, "age_days": 30, "semantic_score": 0.5},
        {"id": "B", "views": 1000000, "likes": 50000, "age_days": 1, "semantic_score": 0.9},
        {"id": "C", "views": 50000, "likes": 2000, "age_days": 15, "semantic_score": 0.7},
    ]

    ranked_list = ranking_engine_service.rank(candidates, user_id=None)

    assert len(ranked_list) == 3
    assert ranked_list[0]['id'] == 'B'
    assert ranked_list[2]['id'] == 'A'
    assert ranked_list[0]['score'] > ranked_list[1]['score'] > ranked_list[2]['score']
