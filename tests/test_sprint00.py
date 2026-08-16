"""
tests/test_sprint00.py
Sprint 00 — Full Test Suite (v2 — Redis-resilient)

Run: cd /workspaces/fwg_ai_os && PYTHONPATH=$(pwd) pytest tests/test_sprint00.py -v
"""
import os
import pytest

# ── Always set PYTHONPATH before any imports ──────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fwg.db")
os.environ.setdefault("REDIS_URL",    "redis://localhost:6379")
os.environ.setdefault("QDRANT_HOST",  "localhost")
os.environ.setdefault("QDRANT_PORT",  "6333")


def _redis_available() -> bool:
    try:
        import redis
        redis.from_url(os.environ["REDIS_URL"], socket_timeout=1).ping()
        return True
    except Exception:
        return False


REDIS_AVAILABLE = _redis_available()


# ─── Fixtures ────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    from backend.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c

    import pathlib
    pathlib.Path("test_fwg.db").unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_session():
    from backend.models.db import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    yield db
    db.close()


# ─── 1. Health ────────────────────────────────────────────────────────
class TestHealth:

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert "version" in data, f"Missing 'version' key. Got: {list(data.keys())}"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200, f"Expected 200, got {r.status_code} — deploy new main.py"

    def test_discovery_health(self, client):
        r = client.get("/api/v1/discovery/health")
        assert r.status_code == 200

    def test_feedback_health(self, client):
        r = client.get("/api/v1/feedback/health")
        assert r.status_code == 200

    def test_ranking_health(self, client):
        r = client.get("/api/v1/ranking/health")
        assert r.status_code == 200

    def test_nexus_health(self, client):
        r = client.get("/api/v1/nexus/health")
        assert r.status_code == 200, "Deploy nexus.py + update router.py"


# ─── 2. Ranking ───────────────────────────────────────────────────────
class TestRankingEngine:

    def test_basic_ranking(self):
        from backend.services.ranking_engine import ranking_engine_service
        items = [
            {"id": "1", "views": 100000, "likes": 5000, "age_days": 1},
            {"id": "2", "views": 100,    "likes": 1,    "age_days": 300},
        ]
        ranked = ranking_engine_service.rank(items)
        assert ranked[0]["id"] == "1"

    def test_weights_sum_to_one(self):
        from backend.services.ranking_engine import RankingEngine
        total = sum(RankingEngine.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_score_clamped(self):
        from backend.services.ranking_engine import ranking_engine_service
        items = [{"id": "x", "views": 999999999, "likes": 999999, "age_days": 0}]
        ranked = ranking_engine_service.rank(items)
        assert 0.0 <= ranked[0]["score"] <= 1.0

    def test_ranking_endpoint(self, client):
        r = client.post("/api/v1/ranking/rank", json={
            "candidates": [
                {"id": "1", "title": "High", "views": 50000, "likes": 2000},
                {"id": "2", "title": "Low",  "views": 100,   "likes": 1},
            ]
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ranked"][0]["id"] == "1"

    def test_empty_candidates(self, client):
        r = client.post("/api/v1/ranking/rank", json={"candidates": []})
        assert r.status_code == 422


# ─── 3. Feedback ─────────────────────────────────────────────────────
class TestFeedback:

    def test_valid_like(self, client):
        r = client.post("/api/v1/feedback/", json={
            "user_id":    "test_user",
            "item_id":    "video_123",
            "event_type": "like",
            "value":      1.0,
        })
        assert r.status_code == 200

    def test_valid_watch_time(self, client):
        r = client.post("/api/v1/feedback/", json={
            "user_id":    "test_user",
            "item_id":    "video_456",
            "event_type": "watch_time",
            "value":      0.85,
        })
        assert r.status_code == 200

    def test_invalid_event_type(self, client):
        r = client.post("/api/v1/feedback/", json={
            "user_id":    "test_user",
            "item_id":    "video_789",
            "event_type": "invalid_event",
            "value":      1.0,
        })
        assert r.status_code == 422

    def test_invalid_value_range(self, client):
        r = client.post("/api/v1/feedback/", json={
            "user_id":    "test_user",
            "item_id":    "video_000",
            "event_type": "like",
            "value":      999.0,
        })
        assert r.status_code == 422


# ─── 4. Personalization ───────────────────────────────────────────────
class TestPersonalization:

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not running")
    def test_update_and_profile(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        uid = "pytest_user_001"
        pe.update(uid, "v1", "like", 1.0, {
            "platform": "youtube",
            "tags": ["AI", "tech"],
            "channel": "test_channel",
        })
        profile = pe.get_profile(uid)
        assert len(profile.get("top_interests", {})) > 0

    @pytest.mark.skipif(not REDIS_AVAILABLE, reason="Redis not running")
    def test_bonus_for_liked_content(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        uid = "pytest_user_bonus"
        pe.update(uid, "v1", "like", 1.0, {"platform": "youtube", "tags": ["AI"]})
        bonus_ai    = pe.get_personalization_bonus({"id": "x", "platform": "youtube", "tags": ["AI"]}, uid)
        bonus_other = pe.get_personalization_bonus({"id": "y", "platform": "tiktok",  "tags": ["food"]}, uid)
        assert bonus_ai >= bonus_other

    def test_cold_start_returns_zero(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        bonus = pe.get_personalization_bonus({"id": "x"}, "brand_new_user_999")
        assert bonus == 0.0


# ─── 5. Schemas ───────────────────────────────────────────────────────
class TestSchemas:

    def test_content_item_alias(self):
        """ContentItem accepts 'id' field via alias."""
        from backend.models.schemas import ContentItem
        # ✅ Only required fields: id (alias), title
        item = ContentItem(**{
            "id":    "abc123",
            "title": "Test Video",
        })
        assert item.item_id == "abc123"

    def test_content_item_with_url(self):
        from backend.models.schemas import ContentItem
        item = ContentItem(**{
            "id":       "abc123",
            "title":    "Test Video",
            "url":      "https://youtube.com/watch?v=abc",
            "platform": "youtube",
        })
        assert item.item_id == "abc123"
        assert item.platform == "youtube"

    def test_discovery_request_minimal(self):
        from backend.models.schemas import DiscoveryRequest
        req = DiscoveryRequest(topic="AI trends")
        assert req.topic == "AI trends"
        assert req.user_id is None

    def test_feedback_event(self):
        from backend.models.schemas import FeedbackEvent
        event = FeedbackEvent(
            user_id="u1", item_id="v1",
            event_type="like", value=1.0,
        )
        assert event.event_type == "like"


# ─── 6. Tool Planner ─────────────────────────────────────────────────
class TestToolPlanner:

    def test_trend_routing(self):
        from backend.lim.tool_planner import ToolPlanner
        tp = ToolPlanner()
        assert tp.decide("find trending viral videos") == "trend_scanner"

    def test_discovery_routing(self):
        from backend.lim.tool_planner import ToolPlanner
        tp = ToolPlanner()
        assert tp.decide("discover content about AI") == "discovery_engine"

    def test_default_fallback(self):
        from backend.lim.tool_planner import ToolPlanner
        tp = ToolPlanner()
        assert tp.decide("how do I cook pasta?") == "llm"


# ─── 7. Task Planner ─────────────────────────────────────────────────
class TestTaskPlanner:

    def test_trend_plan_has_3_stages(self):
        from backend.aios.task_planner import task_planner_service
        plan = task_planner_service.create_plan("find viral trend creators", goal_id=1)
        assert len(plan) == 3

    def test_trend_stage1_is_scanner(self):
        from backend.aios.task_planner import task_planner_service
        plan = task_planner_service.create_plan("trending AI content", goal_id=2)
        assert plan[0][0].tool_name == "trend_scanner"

    def test_generic_plan_parallel_stage1(self):
        from backend.aios.task_planner import task_planner_service
        plan = task_planner_service.create_plan("research machine learning", goal_id=3)
        assert len(plan[0]) == 2

    def test_trend_keyword_extraction(self):
        from backend.aios.task_planner import TaskPlanner
        kw = TaskPlanner._extract_trend_keyword("find viral topic creators")
        assert kw in ["viral topic", "viral", "viral trend"]


# ─── 8. Reward Engine ────────────────────────────────────────────────
class TestRewardEngine:

    def test_like_positive(self):
        from backend.learning.reward import RewardEngine
        assert RewardEngine.calculate_from_str("like", 1.0) > 0

    def test_skip_negative(self):
        from backend.learning.reward import RewardEngine
        assert RewardEngine.calculate_from_str("skip", 1.0) < 0

    def test_watch_time_scales(self):
        from backend.learning.reward import RewardEngine
        assert RewardEngine.calculate_from_str("watch_time", 0.95) > \
               RewardEngine.calculate_from_str("watch_time", 0.05)

    def test_unknown_returns_zero(self):
        from backend.learning.reward import RewardEngine
        assert RewardEngine.calculate_from_str("unknown_event") == 0


# ─── 9. DB Models ────────────────────────────────────────────────────
class TestDBModels:

    def test_create_goal(self, db_session):
        from backend.models.db import Goal
        goal = Goal(description="Test goal", user_id="user1")
        db_session.add(goal)
        db_session.commit()
        db_session.refresh(goal)
        assert goal.id is not None
        assert goal.status == "pending"
        db_session.delete(goal)
        db_session.commit()

    def test_video_model_exists(self):
        """Check Video model is importable from db.py."""
        try:
            from backend.models.db import Video
            assert Video is not None
        except ImportError:
            pytest.fail("Video not in db.py — deploy new db.py from outputs/db.py")

    def test_channel_model_exists(self):
        """Check Channel model is importable from db.py."""
        try:
            from backend.models.db import Channel
            assert Channel is not None
        except ImportError:
            pytest.fail("Channel not in db.py — deploy new db.py from outputs/db.py")

    def test_create_video(self, db_session):
        try:
            from backend.models.db import Video
        except ImportError:
            pytest.skip("Video model not yet deployed")

        v = Video(title="Test", thumbnail_url="https://x.com/t.jpg",
                  semantic_tags=["AI"], viral_potential=85.0)
        db_session.add(v)
        db_session.commit()
        assert v.id is not None
        db_session.delete(v)
        db_session.commit()


# ─── 10. Discovery ───────────────────────────────────────────────────
class TestDiscovery:

    def test_simple_mode_returns_200(self, client):
        r = client.post(
            "/api/v1/discovery/discover?mode=simple",
            json={"topic": "AI trends"},
        )
        assert r.status_code == 200, \
            f"Got {r.status_code}: {r.text[:200]}"

    def test_response_has_ranked_content(self, client):
        r = client.post(
            "/api/v1/discovery/discover?mode=simple",
            json={"topic": "AI trends", "user_id": "u1"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "ranked_content" in data
        assert isinstance(data["ranked_content"], list)
