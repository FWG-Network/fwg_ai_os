"""
scripts/sprint00_verify.py
Sprint 00 — System Verification Script

Run this before starting the server:
  python scripts/sprint00_verify.py

Checks:
  1. All imports work
  2. .env configured
  3. Redis reachable
  4. Qdrant reachable
  5. Database init
  6. Core logic (ranking, personalization)
  7. API routes registered
"""
import sys
import os
import traceback

# ── Colors ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

passed = 0
failed = 0
warned = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}✅ {msg}{RESET}")


def fail(msg, err=""):
    global failed
    failed += 1
    print(f"  {RED}❌ {msg}{RESET}")
    if err:
        print(f"     {RED}→ {err}{RESET}")


def warn(msg):
    global warned
    warned += 1
    print(f"  {YELLOW}⚠️  {msg}{RESET}")


def section(title):
    print(f"\n{BOLD}{BLUE}{'─'*50}{RESET}")
    print(f"{BOLD}{BLUE}  {title}{RESET}")
    print(f"{BOLD}{BLUE}{'─'*50}{RESET}")


# ─── 1. Environment ───────────────────────────────────────────────────
section("1. Environment Variables")

from dotenv import load_dotenv
load_dotenv(override=True)

checks = {
    "DATABASE_URL":   ("required", "sqlite:///./fwg_ai_os.db"),
    "REDIS_URL":      ("required", "redis://localhost:6379"),
    "QDRANT_HOST":    ("required", "localhost"),
    "YOUTUBE_API_KEY":("optional", ""),
    "HF_TOKEN":       ("optional", ""),
    "AGENT_URL":      ("optional", ""),
    "INGEST_API_KEY": ("optional", ""),
    "CORS_ORIGINS":   ("optional", ""),
}

for key, (importance, default) in checks.items():
    val = os.getenv(key, "")
    if val:
        ok(f"{key} = set ({'***' if 'KEY' in key or 'TOKEN' in key else val[:40]})")
    elif importance == "required":
        if default:
            warn(f"{key} not set — using default: {default}")
        else:
            fail(f"{key} is REQUIRED but not set")
    else:
        warn(f"{key} not set (optional)")


# ─── 2. Python Imports ────────────────────────────────────────────────
section("2. Core Imports")

import_checks = [
    ("fastapi",          "FastAPI"),
    ("sqlalchemy",       "SQLAlchemy"),
    ("pydantic",         "Pydantic"),
    ("redis",            "Redis"),
    ("httpx",            "HTTPX"),
    ("dotenv",           "python-dotenv"),
    ("uvicorn",          "Uvicorn"),
    ("celery",           "Celery"),
    ("yaml",             "PyYAML"),
    ("qdrant_client",    "Qdrant Client"),
]

for module, name in import_checks:
    try:
        __import__(module)
        ok(f"{name}")
    except ImportError as e:
        fail(f"{name} not installed", str(e))


# ─── 3. Backend Imports ───────────────────────────────────────────────
section("3. Backend Module Imports")

backend_modules = [
    "backend.core.config",
    "backend.core.logger",
    "backend.models.db",
    "backend.models.schemas",
    "backend.services.ranking_engine",
    "backend.services.personalization_engine",
    "backend.services.discovery_engine",
    "backend.services.worker_client",
    "backend.services.nexus_engine",
    "backend.lim.vector_memory",
    "backend.lim.llm_router",
    "backend.lim.rag_pipeline",
    "backend.lim.orchestrator",
    "backend.lim.tool_planner",
    "backend.aios.task_planner",
    "backend.aios.executor",
    "backend.aios.reflection",
    "backend.aios.autonomous_loop",
    "backend.learning.events",
    "backend.learning.reward",
    "backend.learning.online_learning",
    "backend.api.router",
]

for module in backend_modules:
    try:
        __import__(module)
        ok(module.split(".")[-1])
    except Exception as e:
        fail(module, str(e)[:80])


# ─── 4. Redis ─────────────────────────────────────────────────────────
section("4. Redis Connection")

try:
    import redis as redis_lib
    from backend.core.config import settings
    r = redis_lib.from_url(settings.REDIS_URL, socket_timeout=3)
    r.ping()
    info = r.info("memory")
    ok(f"Connected — used memory: {info['used_memory_human']}")

    # Test write/read
    r.set("sprint00:test", "ok", ex=10)
    val = r.get("sprint00:test")
    ok(f"Read/Write working — value: {val}")
except Exception as e:
    fail("Redis not reachable", str(e))


# ─── 5. Qdrant ────────────────────────────────────────────────────────
section("5. Qdrant Connection")

try:
    from qdrant_client import QdrantClient
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=5,
    )
    cols = client.get_collections().collections
    ok(f"Connected — {len(cols)} collections: {[c.name for c in cols]}")
except Exception as e:
    fail("Qdrant not reachable", str(e))


# ─── 6. Database ─────────────────────────────────────────────────────
section("6. Database")

try:
    from backend.models.db import init_db, SessionLocal, Goal, Task, Video, Channel
    import sqlalchemy
    init_db()
    ok("Tables created/verified")

    db = SessionLocal()
    db.execute(sqlalchemy.text("SELECT 1"))
    db.close()
    ok("Connection working")

    # Check tables exist
    for model in [Goal, Task, Video, Channel]:
        count = SessionLocal().query(model).count()
        ok(f"{model.__tablename__}: {count} rows")
except Exception as e:
    fail("Database error", str(e))


# ─── 7. Core Logic ───────────────────────────────────────────────────
section("7. Core Business Logic")

try:
    from backend.services.ranking_engine import ranking_engine_service
    test_items = [
        {"id": "1", "title": "AI Video", "views": 10000, "likes": 500, "age_days": 5},
        {"id": "2", "title": "Cooking",  "views": 500,   "likes": 10,  "age_days": 30},
    ]
    ranked = ranking_engine_service.rank(test_items)
    assert ranked[0]["score"] > ranked[1]["score"]
    ok(f"RankingEngine: '{ranked[0]['title']}' ranked #1 (score={ranked[0]['score']:.3f})")
except Exception as e:
    fail("RankingEngine", str(e))

try:
    from backend.services.personalization_engine import personalization_engine_service
    personalization_engine_service.update(
        "sprint00_test_user", "vid_test", "like", 1.0,
        {"platform": "youtube", "tags": ["AI", "tech"]}
    )
    profile = personalization_engine_service.get_profile("sprint00_test_user")
    ok(f"PersonalizationEngine: {len(profile.get('top_interests', {}))} interests learned")
except Exception as e:
    fail("PersonalizationEngine", str(e))

try:
    from backend.lim.tool_planner import ToolPlanner
    tp = ToolPlanner()
    assert tp.decide("find trending viral AI videos") == "trend_scanner"
    assert tp.decide("discover content about tech") == "discovery_engine"
    assert tp.decide("rank these results") == "ranking_engine"
    ok("ToolPlanner: routing decisions correct")
except Exception as e:
    fail("ToolPlanner", str(e))

try:
    from backend.aios.task_planner import task_planner_service
    plan = task_planner_service.create_plan("find viral trend creators", goal_id=1)
    assert len(plan) == 3    # 3 stages
    assert plan[0][0].tool_name == "trend_scanner"
    ok(f"TaskPlanner: {len(plan)} stages, Stage1 tool='{plan[0][0].tool_name}'")
except Exception as e:
    fail("TaskPlanner", str(e))


# ─── 8. API Routes ────────────────────────────────────────────────────
section("8. API Routes")

try:
    from backend.api.router import api_router
    routes = [(r.path, list(r.methods)) for r in api_router.routes if hasattr(r, 'methods')]
    ok(f"{len(routes)} routes registered")
    for path, methods in routes[:8]:
        ok(f"  {methods[0]:6} {path}")
    if len(routes) > 8:
        ok(f"  ... and {len(routes)-8} more")
except Exception as e:
    fail("API Router", str(e))


# ─── 9. Config ────────────────────────────────────────────────────────
section("9. LLM Config")

try:
    import yaml, os
    config_path = "config/models.yml"
    if os.path.exists(config_path):
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        routing = cfg.get("model_routing", {})
        ok(f"models.yml loaded — {len(routing)} routes")
        ok(f"default model: {routing.get('default', 'NOT SET')}")
    else:
        warn("config/models.yml not found — LLMRouter uses defaults")
except Exception as e:
    fail("models.yml", str(e))


# ─── Summary ─────────────────────────────────────────────────────────
section("SPRINT 00 SUMMARY")

total = passed + failed + warned
print(f"\n  Total checks:  {total}")
print(f"  {GREEN}Passed:  {passed}{RESET}")
print(f"  {YELLOW}Warnings: {warned}{RESET}")
print(f"  {RED}Failed:  {failed}{RESET}")

if failed == 0:
    print(f"\n  {GREEN}{BOLD}🎉 ALL CHECKS PASSED — Ready to launch!{RESET}")
    print(f"\n  {GREEN}python -m uvicorn backend.main:app --reload --port 8000{RESET}")
elif failed <= 3:
    print(f"\n  {YELLOW}{BOLD}⚠️  Minor issues — fix then launch{RESET}")
else:
    print(f"\n  {RED}{BOLD}❌ Critical issues — fix before launching{RESET}")

sys.exit(0 if failed == 0 else 1)
