# backend/services/trend_analysis_service.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case

# 🚀 UPGRADE V3: Import Creator and CreatorMention
from ..models.db import Creator, CreatorMention

class TrendAnalysisService:
    
    # 🚀 UPGRADE V3: Helper function to translate data into insight
    def _get_trend_lifecycle(self, velocity: float, mentions_last_7d: int) -> str:
        """Determines the lifecycle stage of a trend based on velocity and volume."""
        if velocity > 3.0 and mentions_last_7d < 20:
            return "🚀 Emerging"  # High acceleration, low base = New and exciting!
        if velocity >= 1.0 and velocity <= 3.0 and mentions_last_7d >= 20:
            return "⭐ Peaking"   # Stable growth on a high base = Established trend
        if velocity < 1.0 and mentions_last_7d > 10:
            return "📉 Fading"    # Decelerating = The trend is likely over
        
        return "⏳ Stable"       # Low activity

    # 🚀 UPGRADE V3: The main function is now more efficient and provides richer insights
    def get_trend_briefing(self, db: Session) -> list[dict]:
        """
        Calculates mention velocity and determines trend lifecycle for all recently active creators
        using a single, efficient database query.
        """
        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        # 🚀 UPGRADE V3: A single, powerful query to replace the loop.
        # This query groups by creator and calculates everything on the database side.
        creator_stats = db.query(
            Creator.handle,
            # Count mentions in the last 24 hours
            func.count(case((CreatorMention.mentioned_at >= one_day_ago, 1))).label('mentions_24h'),
            # Count mentions in the last 7 days
            func.count(case((CreatorMention.mentioned_at >= seven_days_ago, 1))).label('mentions_7d')
        ).join(CreatorMention, Creator.id == CreatorMention.creator_id)\
         .group_by(Creator.handle)\
         .having(func.count(case((CreatorMention.mentioned_at >= one_day_ago, 1))) > 0)\
         .all()

        results = []
        for handle, mentions_24h, mentions_7d in creator_stats:
            # The same velocity logic as before, but now applied to the pre-calculated stats
            avg_daily_mentions = (mentions_7d / 7) if mentions_7d > 0 else 0.1
            velocity = mentions_24h / avg_daily_mentions if avg_daily_mentions > 0 else mentions_24h * 10
            
            # Translate the numbers into a human-readable lifecycle stage
            lifecycle = self._get_trend_lifecycle(velocity, mentions_7d)

            results.append({
                "handle": handle,
                "mentions_last_24h": mentions_24h,
                "mentions_last_7d": mentions_7d,
                "velocity_score": round(velocity, 2),
                "lifecycle_stage": lifecycle  # ★ The new, actionable insight! ★
            })

        # Rank by the highest velocity
        results.sort(key=lambda x: x["velocity_score"], reverse=True)
        return results

trend_analysis_service = TrendAnalysisService()
