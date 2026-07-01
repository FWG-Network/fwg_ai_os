"""
tests/test_sprint00.py
Sprint 00 — Full Test Suite

Run: pytest tests/test_sprint00.py -v
"""
import pytest
from fastapi.testclient import TestClient


# ─── Fixtures ────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    """FastAPI test client — uses SQLite in-memory."""
    import os
    os.environ.setdefault("DATABASE_URL", "sqlite:///./test_fwg.db")
    os.environ.setdefault("REDIS_URL",    "redis://localhost:6379")
    os.environ.setdefault("QDRANT_HOST",  "localhost")

    from backend.main import app
    with TestClient(app) as c:
        yield c

    # Cleanup
    import pathlib
    pathlib.Path("test_fwg.db").unlink(missing_ok=True)


@pytest.fixture(scope="session")
def db_session():
    """DB session for direct model tests."""
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
        assert "version" in data

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert "services" in r.json()

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
        assert r.status_code == 200


# ─── 2. Ranking Engine ────────────────────────────────────────────────
class TestRankingEngine:

    def test_basic_ranking(self):
        from backend.services.ranking_engine import ranking_engine_service
        items = [
            {"id": "1", "views": 100000, "likes": 5000, "age_days": 1},
            {"id": "2", "views": 100,    "likes": 1,    "age_days": 300},
        ]
        ranked = ranking_engine_service.rank(items)
        assert ranked[0]["id"] == "1"
        assert ranked[0]["score"] > ranked[1]["score"]

    def test_weights_sum_to_one(self):
        from backend.services.ranking_engine import RankingEngine
        total = sum(RankingEngine.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum = {total}, expected 1.0"

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
        assert data["total"] == 2
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
        assert r.json()["user_id"] == "test_user"

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
            "value":      999.0,   # out of range
        })
        assert r.status_code == 422


# ─── 4. Personalization ───────────────────────────────────────────────
class TestPersonalization:

    def test_update_and_profile(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        uid = "pytest_user_001"

        pe.update(uid, "v1", "like", 1.0, {
            "platform": "youtube",
            "tags": ["AI", "tech"],
            "channel": "test_channel",
        })
        pe.update(uid, "v2", "skip", 1.0, {
            "platform": "tiktok",
            "tags": ["cooking"],
        })

        profile = pe.get_profile(uid)
        interests = profile.get("top_interests", {})
        assert len(interests) > 0

    def test_bonus_for_liked_content(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        uid = "pytest_user_bonus"

        pe.update(uid, "v1", "like", 1.0, {
            "platform": "youtube", "tags": ["AI"]
        })

        ai_item     = {"id": "x", "platform": "youtube", "tags": ["AI"]}
        other_item  = {"id": "y", "platform": "tiktok",  "tags": ["food"]}

        bonus_ai    = pe.get_personalization_bonus(ai_item,    uid)
        bonus_other = pe.get_personalization_bonus(other_item, uid)

        assert bonus_ai >= bonus_other

    def test_cold_start_returns_zero(self):
        from backend.services.personalization_engine import personalization_engine_service as pe
        bonus = pe.get_personalization_bonus({"id": "x"}, "brand_new_user_999")
        assert bonus == 0.0


# ─── 5. Schemas ───────────────────────────────────────────────────────
class TestSchemas:

    def test_content_item_alias(self):
        from backend.models.schemas import ContentItem
        item = ContentItem(**{
            "id":       "abc123",
            "title":    "Test Video",
            "url":      "https://youtube.com/watch?v=abc",
            "platform": "youtube",
        })
        assert item.item_id == "abc123"

    def test_discovery_request(self):
        from backend.models.schemas import DiscoveryRequest
        req = DiscoveryRequest(topic="AI trends", user_id="u1")
        assert req.topic == "AI trends"

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
        assert tp.decide("what is emerging creator")  == "trend_scanner"

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
        assert len(plan[0]) == 2    # Stage 1 has 2 parallel tasks

    def test_trend_keyword_extraction(self):
        from backend.aios.task_planner import TaskPlanner
        tp = TaskPlanner()
        kw = tp._extract_trend_keyword("find viral topic creators")
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
        high = RewardEngine.calculate_from_str("watch_time", 0.95)
        low  = RewardEngine.calculate_from_str("watch_time", 0.05)
        assert high > low

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

    def test_create_video(self, db_session):
        from backend.models.db import Video
        video = Video(
            title="Test Video",
            thumbnail_url="https://example.com/thumb.jpg",
            semantic_tags=["AI", "tech"],
            viral_potential=85.0,
            quality_score=90.0,
        )
        db_session.add(video)
        db_session.commit()
        assert video.id is not None

    def test_create_channel(self, db_session):
        from backend.models.db import Channel
        ch = Channel(id="test_channel", name="Test Channel", platform="youtube")
        db_session.add(ch)
        db_session.commit()
        result = db_session.query(Channel).filter_by(id="test_channel").first()
        assert result is not None


# ─── 10. Discovery Endpoint ───────────────────────────────────────────
class TestDiscovery:

    def test_simple_mode_no_api_key(self, client):
        """Simple mode should return result even without YouTube API key."""
        r = client.post(
            "/api/v1/discovery/discover?mode=simple",
            json={"topic": "AI trends", "user_id": "test_user"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "mode" in data
        assert "total" in data
        assert "ranked_content" in data

    def test_response_has_required_fields(self, client):
        r = client.post(
            "/api/v1/discovery/discover?mode=simple",
            json={"topic": "test topic"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "ranked_content" in data
        assert isinstance(data["ranked_content"], list)
