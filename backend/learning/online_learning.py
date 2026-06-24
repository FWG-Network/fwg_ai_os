# For simplicity, we assume profile is a dictionary-like object
# In production, this would be our UserProfile schema object

class OnlineLearning:
    LEARNING_RATE = 0.1

    def update_interest(self, profile: dict, tags: list, reward: int):
        """Updates user interest scores based on the reward."""
        if "interests" not in profile:
            profile["interests"] = {}

        for tag in tags:
            if tag not in profile["interests"]:
                profile["interests"][tag] = 0
            
            # Apply learning: increase for positive, decrease for negative
            update_value = reward * self.LEARNING_RATE
            profile["interests"][tag] += update_value

        return profile
