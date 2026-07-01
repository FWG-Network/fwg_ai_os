# Sprint 00 — Stabilize & Verify

**Goal:** Foundation stable, all tests pass, server runs clean.

## Checklist

### Step 1 — Copy All Files

Copy files from previous sessions to correct locations:

```
backend/core/config.py
backend/core/logger.py
backend/core/services.py
backend/models/db.py              ← includes Video, Channel, SeedConcept
backend/models/schemas.py
backend/services/ranking_engine.py
backend/services/personalization_engine.py
backend/services/discovery_engine.py
backend/services/worker_client.py
backend/services/nexus_engine.py   ← NEW: Predator + Genesis
backend/services/multimodal_engine.py
backend/services/trend_analysis_service.py
backend/services/connectors/youtube.py
backend/lim/vector_memory.py
backend/lim/rag_pipeline.py
backend/lim/llm_router.py
backend/lim/orchestrator.py
backend/lim/prompt_engine.py
backend/lim/tool_planner.py
backend/aios/task_planner.py
backend/aios/executor.py
backend/aios/autonomous_loop.py
backend/aios/reflection.py
backend/aios/agent.py
backend/aios/goal.py
backend/aios/tasks.py
backend/learning/events.py
backend/learning/reward.py
backend/learning/online_learning.py
backend/learning/trainer.py
backend/learning/tasks.py
backend/api/router.py              ← includes nexus endpoint
backend/api/endpoints/discovery.py
backend/api/endpoints/feedback.py
backend/api/endpoints/ranking.py
backend/api/endpoints/nexus.py     ← NEW: /nexus/analyze, /nexus/search
backend/api/endpoints/llm.py
backend/api/endpoints/multimodal.py
backend/api/endpoints/os.py
backend/main.py                    ← CORS_ORIGINS from .env
backend/worker.py
config/models.yml
.env                               ← add CORS_ORIGINS, INGEST_API_KEY
.gitignore
```

---

### Step 2 — Run Verification Script

```bash
python scripts/sprint00_verify.py
```

Expected output:
```
✅ All checks passed — Ready to launch!
```

---

### Step 3 — Run Tests

```bash
# Install test deps
pip install pytest pytest-asyncio httpx

# Run all Sprint 00 tests
pytest tests/test_sprint00.py -v

# Expected: 30+ tests pass
```

---

### Step 4 — Start Server

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Verify startup logs:
```
✅ Database tables ready
✅ Qdrant collections ready
✅ FWG AI-OS v4.0 ready!
```

---

### Step 5 — Test Endpoints Manually

```bash
# Health
curl http://localhost:8000/health

# Discovery (simple)
curl -X POST http://localhost:8000/api/v1/discovery/discover?mode=simple \
  -H "Content-Type: application/json" \
  -d '{"topic": "AI trends", "user_id": "u1"}'

# Feedback
curl -X POST http://localhost:8000/api/v1/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","item_id":"v1","event_type":"like","value":1.0}'

# Ranking
curl -X POST http://localhost:8000/api/v1/ranking/rank \
  -H "Content-Type: application/json" \
  -d '{"candidates":[{"id":"1","views":10000,"likes":500},{"id":"2","views":100,"likes":1}]}'

# Nexus channels
curl http://localhost:8000/api/v1/nexus/channels

# Swagger UI
open http://localhost:8000/docs
```

---

### Sprint 00 Definition of Done

```
☐ scripts/sprint00_verify.py → all green
☐ pytest tests/test_sprint00.py → 0 failures
☐ Server starts without errors
☐ GET /health → all services online
☐ POST /discover → returns ranked_content
☐ POST /feedback → returns received/queued
☐ POST /ranking/rank → returns ranked
☐ GET /nexus/channels → returns []
☐ GET /docs → Swagger UI loads
```

---

### Known Issues to Fix

| Issue | File | Fix |
|-------|------|-----|
| `await rank()` | discovery.py | Remove await |
| `CORS_ORIGINS` hardcoded `*` | main.py | Read from .env |
| `aios.tasks` not found | worker.py | Comment out |
| `utcnow()` deprecated | trend_analysis | Use `timezone.utc` |

---

### Next: Sprint 08 — AI Council

Once Sprint 00 ✅ complete → start Sprint 08 (AI Council MVP).
