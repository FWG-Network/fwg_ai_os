import pytest
# ★★★ FIX: Import from the new central services hub ★★★
from backend.core.services import reward_service
from backend.learning.events import EventType

@pytest.mark.parametrize("event_type, value, expected_reward", [
    (EventType.LIKE, 0.0, 6),
    (EventType.SKIP, 0.0, -6),
    (EventType.WATCH, 0.95, 8),
])
def test_reward_calculation(event_type, value, expected_reward):
    """Tests the central instance of the RewardEngine."""
    calculated_reward = reward_service.calculate(event_type, value)
    assert calculated_reward == expected_reward
