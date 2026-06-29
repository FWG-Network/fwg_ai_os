"""
backend/learning/trainer.py
Trainer — orchestrates reward + learning pipeline.
Uses Dependency Injection for testability.
"""
from backend.core.logger import log


class Trainer:
    """
    Processes user events → updates interest profile.

    Design: Dependency Injection (no circular imports)
    - reward_engine:   calculates reward score
    - learning_engine: applies reward to profile
    """

    def __init__(self, reward_engine, learning_engine):
        self.reward_engine   = reward_engine
        self.learning_engine = learning_engine

    def process_and_update_profile(self, profile: dict, event) -> dict:
        """
        Process event → calculate reward → update profile.
        Returns updated profile (caller handles persistence).

        Stateless: same input → same output (testable).
        """
        try:
            reward = self.reward_engine.calculate(
                event.event_type,
                event.value,
            )
            log.debug(
                f"[Trainer] user={event.user_id} "
                f"event={event.event_type} "
                f"reward={reward:+d}"
            )
        except Exception as e:
            log.warning(f"[Trainer] Reward calc failed: {e} → reward=0")
            reward = 0

        updated = self.learning_engine.update_interest(
            profile=profile,
            tags=event.tags,
            reward=reward,
        )
        return updated


# ⚠️ No instance here — prevents circular imports.
# Create in services.py or tasks.py:
#   trainer = Trainer(reward_engine=RewardEngine(), learning_engine=OnlineLearning())
