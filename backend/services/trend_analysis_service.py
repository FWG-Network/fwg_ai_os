"""
backend/services/trend_analysis_service.py
Trend Analysis — velocity + lifecycle from DB mentions.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from backend.models.db import Creator, CreatorMention
from backend.core.logger import log


class TrendAnalysisService:

    @staticmethod
    def _get_trend_lifecycle(velocity: float, mentions_7d: int) -> str:
        """Classify trend stage from velocity + volume."""
        if velocity > 3.0 and mentions_7d < 20:
            return "🚀 Emerging"   # high accel, low base
        if 1.0 <= velocity <= 3.0 and mentions_7d >= 20:
            return "⭐ Peaking"    # stable growth, high base
        if velocity < 1.0 and mentions_7d > 10:
            return "📉 Fading"     # decelerating
        return "⏳ Stable"

    def get_trend_briefing(self, db: Session) -> list[dict]:
        """
        Single DB query → velocity + lifecycle for all active creators.
        ✅ Fix: timezone.utc (not deprecated utcnow)
        ✅ Fix: error handling
        ✅ Fix: logging
        """
        log.info("[TrendAnalysis] Building trend briefing...")
        try:
            # ✅ Fix: timezone-aware datetimes
            now            = datetime.now(timezone.utc)
            one_day_ago    = now - timedelta(days=1)
            seven_days_ago = now - timedelta(days=7)

            creator_stats = (
                db.query(
                    Creator.handle,
                    func.count(
                        case((CreatorMention.mentioned_at >= one_day_ago, 1))
                    ).label("mentions_24h"),
                    func.count(
                        case((CreatorMention.mentioned_at >= seven_days_ago, 1))
                    ).label("mentions_7d"),
                )
                .join(CreatorMention, Creator.id == CreatorMention.creator_id)
                .group_by(Creator.handle)
                .having(
                    func.count(
                        case((CreatorMention.mentioned_at >= one_day_ago, 1))
                    ) > 0
                )
                .all()
            )

            results = []
            for handle, mentions_24h, mentions_7d in creator_stats:
                avg_daily  = (mentions_7d / 7) if mentions_7d > 0 else 0.1
                velocity   = (mentions_24h / avg_daily) if avg_daily > 0 else mentions_24h * 10
                lifecycle  = self._get_trend_lifecycle(velocity, mentions_7d)

                results.append({
                    "handle":            handle,
                    "mentions_last_24h": mentions_24h,
                    "mentions_last_7d":  mentions_7d,
                    "velocity_score":    round(velocity, 2),
                    "lifecycle_stage":   lifecycle,
                })

            results.sort(key=lambda x: x["velocity_score"], reverse=True)
            log.info(f"[TrendAnalysis] ✅ {len(results)} creators analyzed")
            return results

        except Exception as e:
            log.error(f"[TrendAnalysis] Failed: {e}")
            return []


trend_analysis_service = TrendAnalysisService()
