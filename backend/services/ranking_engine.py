from math import log

class RankingEngine:
    """
    Ranks a list of content candidates based on a multi-factor scoring system.
    (Implementation from our Phase 3 design)
    """
    WEIGHTS = {
        "semantic": 0.40,
        "popularity": 0.20,
        "engagement": 0.15,
        "freshness": 0.15,
    }

    def _popularity_score(self, views):
        return min(log(views + 1) / 10.0, 1.0)

    def _engagement_score(self, likes, views):
        if views == 0: return 0
        return min(likes / views, 1.0)

    def _freshness_score(self, age_days):
        return max(0.0, 1.0 - age_days / 365.0)

    def rank(self, candidates: list[dict], user_profile: dict) -> list[dict]:
        ranked_items = []
        for item in candidates:
            # Mock scores for demonstration
            item['views'] = item.get('views', 1000)
            item['likes'] = item.get('likes', 100)
            item['age_days'] = item.get('age_days', 10)
            item['semantic_score'] = item.get('semantic_score', 0.8)

            pop_score = self._popularity_score(item['views'])
            eng_score = self._engagement_score(item['likes'], item['views'])
            fresh_score = self._freshness_score(item['age_days'])
            
            final_score = (
                item['semantic_score'] * self.WEIGHTS["semantic"] +
                pop_score * self.WEIGHTS["popularity"] +
                eng_score * self.WEIGHTS["engagement"] +
                fresh_score * self.WEIGHTS["freshness"]
            )
            
            item['ranking_score'] = round(final_score, 4)
            ranked_items.append(item)

        # Sort by score, descending
        ranked_items.sort(key=lambda x: x['ranking_score'], reverse=True)
        return ranked_items

ranking_engine_service = RankingEngine()
