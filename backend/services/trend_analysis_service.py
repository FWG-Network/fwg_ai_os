# backend/services/trend_analysis_service.py
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.db import Creator, CreatorMention

class TrendAnalysisService:
    def calculate_mention_velocity(self, db: Session) -> list[dict]:
        """
        Calculates the mention velocity for all creators.
        Velocity = (mentions in last 24h) vs (average daily mentions over last 7 days)
        """
        creators = db.query(Creator).all()
        results = []

        now = datetime.utcnow()
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)

        for creator in creators:
            # Count recent mentions
            recent_mentions = db.query(CreatorMention).filter(
                CreatorMention.creator_id == creator.id,
                CreatorMention.mentioned_at >= one_day_ago
            ).count()

            # Count mentions over a baseline period
            baseline_mentions = db.query(CreatorMention).filter(
                CreatorMention.creator_id == creator.id,
                CreatorMention.mentioned_at >= seven_days_ago
            ).count()
            
            # Avoid division by zero, calculate daily average
            avg_daily_mentions = (baseline_mentions / 7) if baseline_mentions > 0 else 0.1

            # The "Velocity Score"
            # A score > 1 means they are accelerating
            velocity = recent_mentions / avg_daily_mentions if avg_daily_mentions > 0 else recent_mentions * 10

            if recent_mentions > 0: # Only show creators with recent activity
                results.append({
                    "handle": creator.handle,
                    "mentions_last_24h": recent_mentions,
                    "mentions_last_7d": baseline_mentions,
                    "velocity_score": round(velocity, 2)
                })

        # Rank by the highest velocity
        results.sort(key=lambda x: x["velocity_score"], reverse=True)
        return results

trend_analysis_service = TrendAnalysisService()
