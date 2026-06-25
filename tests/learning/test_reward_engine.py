import pytest
from backend.learning.reward import RewardEngine # <-- Import the CLASS
from backend.learning.events import EventType

# ★★★ FIX: Test the class directly, no need for a service instance ★★★
@pytest.mark.parametrize("event_type, value, expected_reward", [
    (EventType.LIKE, 0.0, 6),
    (EventType.SKIP, 0.0, -6),
])
def test_reward_calculation(event_type, value, expected_reward):
    """
    Tests the RewardEngine class logic directly. This is a pure unit test.
    """
    calculated_reward = RewardEngine.calculate(event_type, value)
    assert calculated_reward == expected_reward
