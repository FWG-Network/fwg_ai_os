"""
Personalization Engine v2 — Real-time user interest learning via Redis.

🧠 Learning signals:   like, watch_time, skip, dislike, impression
⚡ Storage:            Redis (connection pool)
🎯 Output:            bonus score [0.0 → 1.0]
✅ Fixes v1:          type hints, bonus formula, pool, normalization
"""
import json
import time
from typing import Dict, List, Optional, Tuple

import redis
from redis.connection import ConnectionPool

from backend.core.config import settings
from backend.core.logger import log


class PersonalizationEngine:

    EVENT_WEIGHTS: Dict[str, float] = {
        "like":        +0.30,
        "watch_time":  +0.20,
        "impression":  +0.05,
        "skip":        -0.15,
        "dislike":     -0.30,
    }

    PROFILE_TTL:   int   = 60 * 60 * 24 * 30
    DECAY_FACTOR:  float = 0.95
    MAX_INTERESTS: int   = 50
    MAX_TAGS:      int   = 8        # v2: ពី 5 → 8
    MAX_SCORE:     float = 5.0      # v2: cap unbounded growth

    _pool: Optional[ConnectionPool] = None

    def __init__(self) -> None:
        self._client: Optional[redis.Redis] = None

    def _get_client(self) -> redis.Redis:
        if self._client is None:
            try:
                if PersonalizationEngine._pool is None:
                    PersonalizationEngine._pool = redis.ConnectionPool.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        max_connections=20,
                        socket_timeout=5,
                        socket_connect_timeout=3,
                    )
                self._client = redis.Redis(connection_pool=PersonalizationEngine._pool)
                self._client.ping()
                log.info("[Personalization] ✅ Redis connected (pool)")
            except Exception as e:
                log.error(f"[Personalization] Redis unavailable: {e}")
                raise
        return self._client

    @staticmethod
    def _interest_key(uid: str) -> str: return f"user:{uid}:interests"
    @staticmethod
    def _history_key(uid: str)  -> str: return f"user:{uid}:history"
    @staticmethod
    def _stats_key(uid: str)    -> str: return f"user:{uid}:stats"

    def update(
        self,
        user_id:    str,
        item_id:    str,
        event_type: str,
        value:      float = 1.0,
        item_meta:  Optional[dict] = None,
    ) -> None:
        try:
            r = self._get_client()
            base_weight      = self.EVENT_WEIGHTS.get(event_type, 0.0)
            effective_weight = base_weight * max(0.0, min(value, 1.0))  # v2: clamp

            if effective_weight == 0:
                return

            signals      = self._extract_signals(item_id, item_meta or {})
            interest_key = self._interest_key(user_id)
            pipe         = r.pipeline()

            for signal in signals:
                pipe.hincrbyfloat(interest_key, signal, effective_weight)

            # v2: cap each signal to MAX_SCORE
            current = r.hgetall(interest_key)
            for field, val in current.items():
                capped = max(-self.MAX_SCORE, min(float(val), self.MAX_SCORE))
                if capped != float(val):
                    pipe.hset(interest_key, field, round(capped, 4))

            history_key = self._history_key(user_id)
            pipe.lpush(history_key, json.dumps({
                "item_id":    item_id,
                "event_type": event_type,
                "value":      value,
                "ts":         time.time(),
            }))
            pipe.ltrim(history_key, 0, 99)

            stats_key = self._stats_key(user_id)
            pipe.hincrby(stats_key, "total_events",        1)
            pipe.hincrby(stats_key, f"event_{event_type}", 1)
            pipe.hset(stats_key, "last_active", str(time.time()))

            for key in [interest_key, history_key, stats_key]:
                pipe.expire(key, self.PROFILE_TTL)

            pipe.execute()
            log.info(
                f"[Personalization] user={user_id} "
                f"event={event_type}({value:+.1f}) "
                f"signals={signals} weight={effective_weight:+.2f}"
            )
            self._trim_interests(r, user_id)

        except Exception as e:
            log.warning(f"[Personalization] Update skipped: {e}")

    def get_personalization_bonus(self, item: dict, user_id: str) -> float:
        """
        v2 FIX: avg = total / matched  (មិនមែន / len(signals))
        normalize: bonus = avg / MAX_SCORE → guaranteed [0.0, 1.0]
        """
        try:
            r         = self._get_client()
            interests = r.hgetall(self._interest_key(user_id))

            if not interests:
                return 0.0

            signals = self._extract_signals(item.get("id", ""), item)
            if not signals:
                return 0.0

            total   = 0.0
            matched = 0

            for signal in signals:
                score = float(interests.get(signal, 0.0))
                if score != 0.0:
                    total   += score
                    matched += 1

            if matched == 0:
                return 0.0

            avg   = total / matched                         # v2: ចែក matched
            bonus = max(0.0, min(avg / self.MAX_SCORE, 1.0))  # v2: normalize

            log.debug(
                f"[Personalization] user={user_id} item={item.get('id')} "
                f"bonus={bonus:.3f} matched={matched}/{len(signals)}"
            )
            return bonus

        except Exception as e:
            log.warning(f"[Personalization] Bonus skipped: {e}")
            return 0.0

    def get_profile(self, user_id: str) -> dict:
        try:
            r         = self._get_client()
            interests = r.hgetall(self._interest_key(user_id))
            stats     = r.hgetall(self._stats_key(user_id))
            history   = r.lrange(self._history_key(user_id), 0, 9)

            sorted_interests: List[Tuple[str, float]] = sorted(
                {k: float(v) for k, v in interests.items()}.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            return {
                "user_id":        user_id,
                "top_interests":  dict(sorted_interests[:10]),
                "total_signals":  len(interests),
                "stats":          stats,
                "recent_history": [json.loads(h) for h in history],
            }
        except Exception as e:
            log.warning(f"[Personalization] Get profile failed: {e}")
            return {"user_id": user_id, "interests": {}, "stats": {}}

    def apply_decay(self, user_id: str) -> None:
        try:
            r         = self._get_client()
            interests = r.hgetall(self._interest_key(user_id))
            if not interests:
                return
            pipe = r.pipeline()
            key  = self._interest_key(user_id)
            for field, value in interests.items():
                new_val = float(value) * self.DECAY_FACTOR
                if abs(new_val) < 0.01:
                    pipe.hdel(key, field)
                else:
                    pipe.hset(key, field, round(new_val, 4))
            pipe.execute()
            log.info(f"[Personalization] Decay applied user={user_id}")
        except Exception as e:
            log.warning(f"[Personalization] Decay skipped: {e}")

    @staticmethod
    def _extract_signals(item_id: str, item: dict) -> List[str]:
        """v2: MAX_TAGS 5→8, added creator + language signals."""
        signals: List[str] = []

        if platform := item.get("platform"):
            signals.append(f"platform:{platform.lower()}")

        for tag in item.get("tags", [])[:8]:          # v2: 8 tags
            signals.append(f"tag:{tag.lower().strip()}")

        if channel := item.get("channel"):
            signals.append(f"channel:{channel.lower()}")

        if category := item.get("category"):
            signals.append(f"category:{category.lower()}")

        if source := item.get("source"):
            signals.append(f"source:{source}")

        if creator := item.get("creator"):            # v2: creator loyalty
            signals.append(f"creator:{creator.lower()}")

        if lang := item.get("language"):              # v2: language
            signals.append(f"lang:{lang.lower()}")

        return signals or [f"item:{item_id}"]

    def _trim_interests(self, r: redis.Redis, user_id: str) -> None:
        try:
            key       = self._interest_key(user_id)
            interests = r.hgetall(key)
            if len(interests) <= self.MAX_INTERESTS:
                return
            to_delete = sorted(
                interests.items(),
                key=lambda x: abs(float(x[1])),
            )[:len(interests) - self.MAX_INTERESTS]
            if to_delete:
                r.hdel(key, *[k for k, _ in to_delete])
        except Exception as e:
            log.warning(f"[Personalization] Trim skipped: {e}")


personalization_engine_service = PersonalizationEngine()
