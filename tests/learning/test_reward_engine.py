import pytest
from backend.learning.reward import reward_service

@pytest.mark.parametrize("event_type, value, expected_reward", [
    ("like", 0.0, 6),
    ("skip", 0.0, -6),
    ("share", 0.0, 10),
    ("view", 0.0, 1),
    ("unknown_event", 0.0, 0),
    ("watch", 0.2, -6), # Short watch is penalized like a skip
    ("watch", 0.7, 4),  # Medium watch
    ("watch", 0.95, 8), # Long watch
])
def test_reward_calculation(event_type, value, expected_reward):
    """
    Tests that the RewardEngine calculates the correct reward for various events.
    """
    calculated_reward = reward_service.calculate(event_type, value)
    assert calculated_reward == expected_reward

def test_reward_for_non_existent_event():
    """
    Tests that a completely unknown event type returns a reward of 0.
    """
    reward = reward_service.calculate("made_up_event")
    assert reward == 0
