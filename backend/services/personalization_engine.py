class PersonalizationEngine:
    """
    Applies a personalization bonus to ranked items based on user interests.
    (Implementation from our Phase 4 design)
    """
    
    def _calculate_bonus(self, profile: dict, item_tags: list[str]) -> float:
        """Calculates a personalization score based on matching tags."""
        if not profile or "interests" not in profile:
            return 0.0
        
        bonus = 0.0
        user_interests = profile.get("interests", {})
        
        for tag in item_tags:
            if tag in user_interests:
                # Add a bonus proportional to the user's interest level in that tag
                bonus += user_interests[tag] * 0.01 # Learning rate adjustment
        
        # Cap the bonus to prevent it from overpowering the ranking score
        return min(bonus, 0.3)

    def personalize(self, ranked_items: list[dict], user_profile: dict) -> list[dict]:
        """
        Takes a list of ranked items and adds a personalization score.
        """
        personalized_items = []
        for item in ranked_items:
            bonus = self._calculate_bonus(user_profile, item.get("tags", []))
            
            # Add the bonus to the original ranking score
            item['final_score'] = item.get('ranking_score', 0.0) + bonus
            personalized_items.append(item)
            
        # Re-sort the list based on the new final score
        personalized_items.sort(key=lambda x: x['final_score'], reverse=True)
        return personalized_items

personalization_engine_service = PersonalizationEngine()
