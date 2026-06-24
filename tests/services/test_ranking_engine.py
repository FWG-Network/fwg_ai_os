from backend.services.ranking_engine import ranking_engine_service

def test_ranking_engine_sorts_by_score():
    """Tests if the ranking engine correctly sorts candidates by their final score."""
    candidates = [
        {"id": "A", "views": 100, "likes": 1, "age_days": 30, "semantic_score": 0.5}, # Low score
        {"id": "B", "views": 1000000, "likes": 50000, "age_days": 1, "semantic_score": 0.9}, # High score
        {"id": "C", "views": 50000, "likes": 2000, "age_days": 15, "semantic_score": 0.7}, # Medium score
    ]
    # Mock user profile, not used in this specific ranking logic but required by the function
    mock_profile = {}
    
    ranked_list = ranking_engine_service.rank(candidates, mock_profile)
    
    assert len(ranked_list) == 3
    # Check if the item with the highest expected score is first
    assert ranked_list[0]['id'] == "B"
    # Check if the item with the lowest expected score is last
    assert ranked_list[2]['id'] == "A"
    # Check if scores are in descending order
    assert ranked_list[0]['ranking_score'] > ranked_list[1]['ranking_score'] > ranked_list[2]['ranking_score']
