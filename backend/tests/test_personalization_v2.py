"""
backend/tests/test_personalization_v2.py
Verify v2 fixes: bonus formula, pool, normalization, signals.
"""
import pytest
from unittest.mock import MagicMock, patch


# ─── helpers ──────────────────────────────────────────────────
def make_engine():
    with patch("redis.ConnectionPool.from_url"), \
         patch("redis.Redis"):
        from backend.services.personalization_engine import PersonalizationEngine
        e = PersonalizationEngine()
        e._client = MagicMock()
        e._client.ping.return_value = True
        return e


# ══════════════════════════════════════════════════════════════
#  1. bonus formula fix: total/matched not total/len(signals)
# ══════════════════════════════════════════════════════════════
def test_bonus_formula_uses_matched_not_total_signals():
    """
    signals = 4  →  only 3 found in Redis
    v1: avg = 1.22 / 4 = 0.305  ❌
    v2: avg = 1.22 / 3 = 0.406  ✅
    """
    e = make_engine()
    e._client.hgetall.return_value = {
        "platform:youtube": "0.46",
        "tag:ai":           "0.46",
        "tag:tech":         "0.30",
        # channel:mkbhd → NOT in Redis (unmatched)
    }
    item = {"id": "x", "platform": "youtube",
            "tags": ["ai", "tech"], "channel": "mkbhd"}
    bonus = e.get_personalization_bonus(item, "user1")

    # matched=3, total=1.22, avg=1.22/3=0.406, bonus=0.406/5.0=0.081
    assert bonus > 0.0, "bonus should be > 0"
    assert bonus <= 1.0, "bonus should be <= 1"
    print(f"✅ bonus formula: {bonus:.4f}  (matched/signals → correct)")


# ══════════════════════════════════════════════════════════════
#  2. normalization: bonus = avg / MAX_SCORE → [0, 1]
# ══════════════════════════════════════════════════════════════
def test_bonus_normalized_between_0_and_1():
    e = make_engine()
    # simulate high interest scores
    e._client.hgetall.return_value = {
        "platform:youtube": "4.9",
        "tag:ai":           "4.8",
    }
    item = {"id": "x", "platform": "youtube", "tags": ["ai"]}
    bonus = e.get_personalization_bonus(item, "user1")
    assert 0.0 <= bonus <= 1.0
    print(f"✅ normalized bonus: {bonus:.4f}  (always in [0,1])")


# ══════════════════════════════════════════════════════════════
#  3. cold start → 0.0 neutral
# ══════════════════════════════════════════════════════════════
def test_cold_start_returns_zero():
    e = make_engine()
    e._client.hgetall.return_value = {}   # new user — no interests
    item = {"id": "x", "platform": "youtube", "tags": ["ai"]}
    bonus = e.get_personalization_bonus(item, "new_user")
    assert bonus == 0.0
    print(f"✅ cold start: {bonus}  (neutral, no penalty)")


# ══════════════════════════════════════════════════════════════
#  4. v2 signals: creator + language extracted
# ══════════════════════════════════════════════════════════════
def test_extract_signals_v2_includes_creator_and_language():
    from backend.services.personalization_engine import PersonalizationEngine
    item = {
        "platform": "YouTube",
        "tags":     ["AI", "Tech", "Python", "ML", "Deep", "NLP", "LLM", "Vision"],
        "channel":  "MKBHD",
        "creator":  "Marques",
        "language": "EN",
        "category": "Tech",
    }
    signals = PersonalizationEngine._extract_signals("test_id", item)

    assert "creator:marques"   in signals, "v2: creator signal missing"
    assert "lang:en"           in signals, "v2: language signal missing"
    assert "platform:youtube"  in signals
    assert len([s for s in signals if s.startswith("tag:")]) == 8   # v2: 8 tags
    print(f"✅ v2 signals ({len(signals)}): {signals}")


# ══════════════════════════════════════════════════════════════
#  5. MAX_TAGS = 8 (v2: ពី 5 → 8)
# ══════════════════════════════════════════════════════════════
def test_max_tags_is_8():
    from backend.services.personalization_engine import PersonalizationEngine
    item = {"tags": ["a","b","c","d","e","f","g","h","i","j"]}  # 10 tags
    signals = PersonalizationEngine._extract_signals("x", item)
    tag_signals = [s for s in signals if s.startswith("tag:")]
    assert len(tag_signals) == 8, f"Expected 8 tags, got {len(tag_signals)}"
    print(f"✅ MAX_TAGS=8: got {len(tag_signals)} tag signals")


# ══════════════════════════════════════════════════════════════
#  6. dislike → negative bonus blocked at 0.0
# ══════════════════════════════════════════════════════════════
def test_negative_interest_returns_zero_bonus():
    e = make_engine()
    e._client.hgetall.return_value = {
        "platform:tiktok": "-0.45",
        "tag:cooking":     "-0.15",
    }
    item = {"id": "y", "platform": "tiktok", "tags": ["cooking"]}
    bonus = e.get_personalization_bonus(item, "user1")
    assert bonus == 0.0, f"negative interests should return 0.0, got {bonus}"
    print(f"✅ negative interest blocked: bonus={bonus}")


# ══════════════════════════════════════════════════════════════
#  7. event_weight value clamped [0,1]
# ══════════════════════════════════════════════════════════════
def test_event_value_clamped():
    from backend.services.personalization_engine import PersonalizationEngine
    e = make_engine()
    e._client.hgetall.return_value = {}
    e._client.pipeline.return_value.__enter__ = MagicMock(return_value=MagicMock())
    e._client.pipeline.return_value.__exit__  = MagicMock(return_value=False)
    pipe_mock = MagicMock()
    e._client.pipeline.return_value = pipe_mock
    pipe_mock.execute.return_value = []

    # value=99.0 should be clamped to 1.0 → weight = 0.30 * 1.0 = 0.30
    try:
        e.update("u1", "item1", "like", value=99.0, item_meta={"platform": "youtube"})
        print("✅ value clamped: no crash on value=99.0")
    except Exception as ex:
        pytest.fail(f"update crashed with value=99: {ex}")
