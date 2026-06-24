import pytest
# ★★★ FIX: Import the service instance directly from the correct file ★★★
from backend.learning.reward import reward_service

@pytest.mark.parametrize("event_type, value, expected_reward", [
    ("like", 0.0, 6),
    ("skip", 0.0, -6),
    ("watch", 0.95, 8),
])
def test_reward_calculation(event_type, value, expected_reward):
    """Tests that the RewardEngine calculates the correct reward."""
    calculated_reward = reward_service.calculate(event_type, value)
    assert calculated_reward == expected_reward
