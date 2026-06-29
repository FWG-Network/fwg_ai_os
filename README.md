# 🤖 FWG Autonomous Intelligence Operating System (AI-OS)

> **Production-grade autonomous AI ecosystem** — self-planning, self-executing, and self-learning.  
> Built with FastAPI · PostgreSQL · Redis · Qdrant · Celery · Docker

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Developer Guide](#developer-guide)
- [Deployment](#deployment)

---

## Overview

FWG AI-OS is a **fully autonomous intelligence platform** that discovers, ranks, and recommends content — while continuously learning from user behavior. Given a high-level goal, the system autonomously plans tasks, executes them with specialized AI agents, and reflects on outcomes to improve over time.

### What it does

| Capability | Description |
|------------|-------------|
| 🔍 **Smart Discovery** | Scans competitor channels (PolarRanks, Oogway Ranks) to extract trending creators and content |
| 🎯 **Weighted Ranking** | Scores content across 5 factors: semantic relevance, popularity, engagement, freshness, personalization |
| 🧠 **Personalization** | Learns user interests in real-time from every like, skip, and watch event via Redis |
| 🤖 **Autonomous Execution** | Breaks high-level goals into staged tasks, executes with specialized tools, reflects on results |
| 🔗 **RAG Pipeline** | Retrieves context from Qdrant vector memory before every LLM response |
| 📚 **Online Learning** | Celery workers process feedback asynchronously — API stays fast |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT / FRONTEND                        │
│               POST /discover  |  POST /feedback              │
└──────────────────────────┬──────────────────────────────────┘
                           │ FastAPI (port 8000)
┌──────────────────────────▼──────────────────────────────────┐
│                    API LAYER (FastAPI)                        │
│   /discovery  /feedback  /ranking  /llm  /os  /multimodal   │
└──┬──────────────┬─────────────┬────────────┬───────────────-┘
   │              │             │            │
┌──▼──────┐ ┌────▼──────┐ ┌───▼─────┐ ┌───▼────────────────┐
│Discovery│ │ Feedback  │ │Ranking  │ │  Autonomous OS     │
│ Engine  │ │+ Learning │ │ Engine  │ │  (AIOS Loop)       │
└──┬──────┘ └────┬──────┘ └───┬─────┘ └───┬────────────────-┘
   │             │            │            │
┌──▼─────────────▼────────────▼────────────▼─────────────────┐
│                   INTELLIGENCE LAYER (LIM)                   │
│    LLMOrchestrator → RAGPipeline → LLMRouter → HF Agent     │
└──┬──────────────────────────────────────┬───────────────────┘
   │                                      │
┌──▼──────────┐  ┌──────────────┐  ┌─────▼────────┐
│  PostgreSQL  │  │    Redis     │  │    Qdrant    │
│  (Goals,     │  │  (Profiles,  │  │  (Vectors,   │
│   Tasks,     │  │   Cache,     │  │   Memory,    │
│   Creators)  │  │   Queue)     │  │   Search)    │
└─────────────┘  └──────────────┘  └──────────────┘
                        │
               ┌────────▼────────┐
               │  Celery Worker  │
               │ (async feedback │
               │  + AIOS tasks)  │
               └─────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API** | FastAPI 0.100+ | REST endpoints, async |
| **Database** | PostgreSQL 14 | Goals, Tasks, Creators, Mentions |
| **Cache/Queue** | Redis 7 | User profiles, Celery broker, Discovery cache |
| **Vector DB** | Qdrant 1.18 | Semantic memory, RAG retrieval |
| **Worker** | Celery | Async feedback processing, AIOS tasks |
| **LLM** | HuggingFace Agent / Claude / GPT | Text generation, reasoning |
| **Embeddings** | sentence-transformers | Semantic text encoding |
| **Container** | Docker + Compose | Reproducible environments |

---

## Project Structure

```
fwg_ai_os/
│
├── backend/
│   ├── main.py                        # FastAPI app entry point + lifespan
│   ├── worker.py                      # Celery worker configuration
│   │
│   ├── core/
│   │   ├── config.py                  # Settings from .env (all env vars)
│   │   ├── logger.py                  # Named logger "fwg_ai_os"
│   │   └── services.py                # Central service hub (imports all singletons)
│   │
│   ├── models/
│   │   ├── db.py                      # SQLAlchemy models: Goal, Task, Creator, User
│   │   └── schemas.py                 # Pydantic schemas: DiscoveryRequest, FeedbackEvent...
│   │
│   ├── api/
│   │   ├── router.py                  # Mounts all endpoint routers under /api/v1
│   │   └── endpoints/
│   │       ├── discovery.py           # POST /discover (simple|smart mode)
│   │       ├── feedback.py            # POST /feedback (like, skip, watch_time...)
│   │       ├── ranking.py             # POST /ranking/rank
│   │       ├── llm.py                 # POST /llm/generate, /llm/rag
│   │       ├── multimodal.py          # POST /multimodal/analyze, /multimodal/upload
│   │       └── os.py                  # POST /os/submit_goal, /os/execute, /os/status
│   │
│   ├── services/
│   │   ├── discovery_engine.py        # YouTube search + smart competitor scan
│   │   ├── ranking_engine.py          # 5-factor weighted scoring
│   │   ├── personalization_engine.py  # Redis-backed user interest learning
│   │   ├── worker_client.py           # HTTP client for Celery worker
│   │   ├── multimodal_engine.py       # Text/image/audio → embeddings
│   │   ├── trend_analysis_service.py  # Creator mention velocity + lifecycle
│   │   └── connectors/
│   │       └── youtube.py             # YouTube Data API v3 connector
│   │
│   ├── lim/                           # Language Intelligence Module
│   │   ├── orchestrator.py            # Central LLM brain: plan→retrieve→generate
│   │   ├── rag_pipeline.py            # RAG: retrieve context → augment prompt → generate
│   │   ├── llm_router.py              # Route to HF Agent / HF Inference / fallback
│   │   ├── prompt_engine.py           # Structured prompt templates (trend/rag/discovery...)
│   │   ├── tool_planner.py            # Keyword-based tool routing decision
│   │   └── vector_memory.py           # Qdrant CRUD: add/search/delete
│   │
│   ├── aios/                          # Autonomous OS
│   │   ├── autonomous_loop.py         # Main loop: Plan→Execute(staged)→Reflect
│   │   ├── task_planner.py            # Intent detection → staged TaskModel plan
│   │   ├── executor.py                # Tool router: runs each task with correct service
│   │   ├── reflection.py              # Evaluates outcome: completed/partial/failed
│   │   ├── agent.py                   # LLMAgent (real) + MockLLMAgent (test)
│   │   ├── goal.py                    # Pydantic Goal/Task (in-memory, not DB)
│   │   └── tasks.py                   # Celery AIOS tasks (async wrapper)
│   │
│   └── learning/                      # Online Learning System
│       ├── events.py                  # EventType enum + UserEvent schema
│       ├── reward.py                  # RewardEngine: event → reward score
│       ├── online_learning.py         # Update Redis interests from feedback
│       ├── trainer.py                 # Orchestrates reward + learning (DI pattern)
│       └── tasks.py                   # Celery feedback processing task
│
├── config/
│   └── models.yml                     # LLM routing table (task_type → model)
│
├── cloud_functions/
│   └── main.py                        # TikTok scraper (Google Cloud Function)
│
├── tests/
│   ├── aios/
│   ├── api/
│   ├── learning/
│   └── services/
│
├── logs/                              # app.log (auto-created)
├── .env                               # Environment variables (never commit!)
├── docker-compose.yml                 # PostgreSQL + Redis + Qdrant
├── Dockerfile
└── requirements.txt
```

---

## Quick Start

### Option A — Local Development (Codespace)

```bash
# 1. Clone and enter project
git clone https://github.com/your-org/fwg_ai_os
cd fwg_ai_os

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (see Environment Variables section)

# 5. Start infrastructure (Redis + Qdrant only for dev)
docker compose up -d redis qdrant

# 6. Initialize database
python -c "from backend.models.db import init_db; init_db()"

# 7. Start API server
python -m uvicorn backend.main:app --reload --port 8000
```

### Option B — Full Stack (Docker Compose)

```bash
# Start everything: PostgreSQL + Redis + Qdrant + App
docker compose up --build

# API available at: http://localhost:8000
# Swagger docs at:  http://localhost:8000/docs
```

### Option C — Codespace (Disk-Safe)

```bash
# Docker on /tmp (avoids /workspaces disk full issue)
sudo systemctl stop docker
sudo pkill dockerd
nohup sudo dockerd --data-root /tmp/docker-data &
sleep 5
docker compose up -d redis qdrant

# Redis on /tmp (1MB memory-only, no persistence)
docker run -d --name redis_tmp -p 6379:6379 \
  redis:7 redis-server --save "" --appendonly no

python -m uvicorn backend.main:app --reload --port 8000
```

---

## Environment Variables

Create a `.env` file in the root directory:

```env
# ── App ──────────────────────────────────────────────────────────────
APP_NAME=FWG AI-OS
DEBUG=true
ENV=development

# ── Database ─────────────────────────────────────────────────────────
DATABASE_URL=sqlite:///./fwg_ai_os.db       # Dev: SQLite
# DATABASE_URL=postgresql://aios_user:aios_password@localhost/aios_db  # Prod

POSTGRES_HOST=localhost
POSTGRES_USER=aios_user
POSTGRES_PASSWORD=aios_password
POSTGRES_DB=aios_db

# ── Redis ─────────────────────────────────────────────────────────────
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379

# ── Qdrant ────────────────────────────────────────────────────────────
QDRANT_HOST=localhost
QDRANT_PORT=6333

# ── Worker ────────────────────────────────────────────────────────────
WORKER_HOST=localhost
WORKER_PORT=8001

# ── API Keys ──────────────────────────────────────────────────────────
YOUTUBE_API_KEY=           # YouTube Data API v3 key (required for discovery)
HF_TOKEN=                  # HuggingFace token (required for LLM)
AGENT_URL=https://sereyfwg-agent.hf.space  # HF Space agent URL
APIFY_API_TOKEN=           # Apify (optional: TikTok alternative)
CLOUD_FUNCTION_URL=        # Google Cloud Function URL (TikTok scraper)
```

### Redis DB Allocation

| DB | Service | Purpose |
|----|---------|---------|
| `db=0` | PersonalizationEngine | User interest profiles |
| `db=1` | Celery broker/backend | Task queue |
| `db=2` | DiscoveryEngine | Search result cache (1hr TTL) |

---

## API Reference

Base URL: `http://localhost:8000/api/v1`

### 🔍 Discovery

```http
POST /discovery/discover?mode=smart
Content-Type: application/json

{
  "topic": "AI tools",
  "content_type": "ranking",
  "intent": "find top 10 ranking videos like PolarRanks",
  "user_id": "user123",
  "days_ago": 7,
  "min_views": 1000
}
```

| Parameter | Values | Description |
|-----------|--------|-------------|
| `mode` | `smart` \| `simple` | smart = PolarRanks scan, simple = direct search |
| `content_type` | `trending` \| `ranking` \| `educational` \| `review` \| `news` \| `any` | Video type filter |

**Response:**
```json
{
  "mode": "smart",
  "topic": "AI tools",
  "total": 12,
  "ranked_content": [
    {
      "id": "abc123",
      "title": "Top 10 AI Tools 2025",
      "score": 0.741,
      "_score_debug": {
        "semantic": 0.8,
        "popularity": 0.65,
        "engagement": 0.12,
        "freshness": 0.92,
        "personalization": 0.48
      }
    }
  ],
  "source_creators_found": [["mkbhd", 5], ["linus", 3]],
  "platforms_scanned": ["youtube"]
}
```

### 💬 Feedback

```http
POST /feedback/
Content-Type: application/json

{
  "user_id": "user123",
  "item_id": "abc123",
  "event_type": "like",
  "value": 1.0
}
```

| `event_type` | `value` | Effect |
|-------------|---------|--------|
| `like` | 1.0 | +0.30 interest boost |
| `watch_time` | 0.0–1.0 | +0.20 × completion rate |
| `skip` | 1.0 | -0.15 interest penalty |
| `dislike` | 1.0 | -0.30 strong penalty |
| `impression` | 1.0 | +0.05 weak signal |

### 🤖 Autonomous OS

```http
POST /os/submit_goal
{
  "goal": "find viral AI trends and create briefing report",
  "user_id": "user123"
}
```

**AIOS Execution Plan (auto-generated):**
```
Stage 1: trend_scanner  → scan PolarRanks for "viral"
Stage 2: trend_analyzer → calculate velocity + rank creators
Stage 3: llm_agent      → synthesize briefing report
```

### 🏥 Health Check

```http
GET /health

{
  "system": "FWG AI-OS",
  "services": {
    "database": "✅ online",
    "redis":    "✅ online",
    "qdrant":   "✅ v1.18.2"
  }
}
```

---

## System Components

### Ranking Engine — 5-Factor Score

```
Final Score = Σ (factor × weight)

semantic:        0.40  ← topic relevance (from discovery)
popularity:      0.20  ← log(views) / 10
engagement:      0.15  ← likes / views
freshness:       0.15  ← 1 - (age_days / 365)
personalization: 0.10  ← Redis interest bonus [0–1]
```

### Personalization Engine — Redis Schema

```
user:{id}:interests   → HASH  { "tag:ai": 0.48, "platform:youtube": 0.30 }
user:{id}:history     → LIST  [ {item_id, event_type, ts}, ... ] (last 100)
user:{id}:stats       → HASH  { total_events: 42, last_active: ... }
```

Signals extracted per content item:
- `platform:youtube` — platform preference
- `tag:ai` — topic interest (from video tags)
- `channel:mkbhd` — creator loyalty
- `category:tech` — category preference

### Smart Discovery — How It Works

```
mode=smart:
  1. Scan KNOWN_RANKING_CHANNELS (PolarRanks, Oogway, etc.)
  2. Extract @credited_handles from video descriptions
  3. Search those creators' videos about the topic
  4. Merge with topic-filtered trending search
  5. Rank with 5-factor engine + personalization
```

### AIOS Autonomous Loop

```
Goal submitted
    │
    ▼ TaskPlanner.create_plan()
    │   → detects intent (trend/generic)
    │   → creates staged TaskModel list
    │
    ▼ Executor.execute_task_group() [per stage]
    │   Stage 1: [trend_scanner] parallel
    │   Stage 2: [trend_analyzer]
    │   Stage 3: [llm_agent] → synthesize
    │
    ▼ ReflectionEngine.evaluate()
        → completed / completed_partial / failed
```

---

## Data Flow

### Content Discovery Flow

```
User: "find ranking videos about AI tools"
         │
         ▼
DiscoveryEngine.smart_discover("AI tools")
         │
         ├── youtube.suggest_from_known_channels()
         │       → scan PolarRanks, Oogway...
         │       → extract @mkbhd, @linus from descriptions
         │       → persist Creator + CreatorMention to PostgreSQL
         │
         ├── youtube.search("AI tools top 10") [per creator]
         │
         ▼
RankingEngine.rank(candidates, user_id="user123")
         │
         ├── semantic:        0.40 × 0.80 = 0.320
         ├── popularity:      0.20 × 0.70 = 0.140
         ├── engagement:      0.15 × 0.65 = 0.098
         ├── freshness:       0.15 × 0.90 = 0.135
         └── personalization: 0.10 × 0.48 = 0.048
                                           = 0.741 ✅
```

### Learning Flow

```
User: "like" on video about AI
         │
         ▼
POST /feedback {event_type: "like", item_id: "abc"}
         │
         ├── [Sync] PersonalizationEngine.update()
         │       → Redis: tag:ai +0.30, platform:youtube +0.30
         │
         └── [Async Celery] process_feedback_event_task()
                 → RewardEngine.calculate() → reward = +6
                 → Trainer.process_and_update_profile()
                 → Redis profile updated
```

---

## Developer Guide

### Adding a New Endpoint

```python
# 1. Create backend/api/endpoints/my_endpoint.py
from fastapi import APIRouter
router = APIRouter(prefix="/my_feature", tags=["My Feature"])

@router.post("/action")
async def my_action():
    return {"result": "..."}

# 2. Register in backend/api/router.py
_include("backend.api.endpoints.my_endpoint")
# Done! Auto-discovered, safe import (server won't crash if missing)
```

### Adding a New Tool to AIOS

```python
# 1. Add keyword → tool mapping in backend/lim/tool_planner.py
TOOL_RULES = [
    ("my_new_tool", ["keyword1", "keyword2"]),
    ...
]

# 2. Add execution logic in backend/aios/executor.py
elif tool == "my_new_tool":
    params = task.tool_params or {}
    result = await my_service.do_something(params.get("key"))
    return {"tool": "my_new_tool", "result": result}

# 3. Add task creation in backend/aios/task_planner.py (optional)
TaskModel(
    description="Do something with my tool",
    goal_id=goal_id,
    tool_name="my_new_tool",
    tool_params={"key": "value"},
)
```

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/services/test_ranking_engine.py -v

# With coverage
pytest tests/ --cov=backend --cov-report=html
```

### Logs

```bash
# Real-time server logs
tail -f logs/app.log

# Filter by component
grep "\[Ranking\]" logs/app.log
grep "\[Personalization\]" logs/app.log
grep "ERROR" logs/app.log
```

### Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `500 Internal Server Error` | Check logs | `tail -f logs/app.log` |
| Redis connection refused | Container not running | `docker compose up -d redis` |
| Qdrant unavailable | Container not running | `docker compose up -d qdrant` |
| `ModuleNotFoundError` | Package missing | `pip install -r requirements.txt` |
| Disk full (Codespace) | `/workspaces` 94% | `pip cache purge && docker system prune -f` |
| `DATABASE_URL=None` | `.env` incomplete | Add `DATABASE_URL=sqlite:///./fwg_ai_os.db` |

---

## Deployment

### Docker Compose (Production)

```yaml
# docker-compose.yml services:
# - db      → PostgreSQL 14 (aios_db)
# - redis   → Redis 7      (aios_redis) port 6379
# - qdrant  → Qdrant latest (aios_qdrant) port 6333
```

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d redis qdrant

# Check status
docker compose ps
docker port aios_redis
```

### Environment Setup Checklist

```
☐ .env configured (all required keys set)
☐ YOUTUBE_API_KEY set (required for discovery)
☐ HF_TOKEN set (required for LLM)
☐ AGENT_URL set (HuggingFace Space URL)
☐ Redis running and reachable
☐ Qdrant running and reachable
☐ Database initialized (init_db() called)
☐ logs/ directory exists
```

### LLM Model Routing (`config/models.yml`)

```yaml
model_routing:
  default:   "HF_AGENT"      # Free — uses AGENT_URL + HF_TOKEN
  rag:       "HF_AGENT"      # Long context — free
  reasoning: "claude-haiku-4-5"  # Fast + cheap (needs ANTHROPIC_API_KEY)
  code:      "claude-sonnet-4-6" # High quality (needs ANTHROPIC_API_KEY)
```

---

## 📊 System Status

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI Server | ✅ | port 8000 |
| PostgreSQL | ✅ | SQLite in dev |
| Redis | ✅ | port 6379 |
| Qdrant | ✅ | port 6333, v1.18.2 |
| Celery Worker | ⏳ | Optional for async |
| YouTube API | ⚠️ | Requires API key |
| HF Agent | ⚠️ | Requires HF_TOKEN |
| TikTok (Cloud Function) | 🔜 | Pending deployment |

---

## Architecture Phase History

| Phase | Feature |
|-------|---------|
| 1–4 | Core recommendation: Discovery + Ranking + Personalization |
| 5 | Real-time feedback + Celery workers |
| 7 | Multimodal engine (text/image/audio) |
| 8–9 | LLM Orchestrator + RAG pipeline |
| 10 | Autonomous OS loop |
| 15 | Online learning + RewardEngine |
| 17 | Qdrant vector memory |
| 21 | ToolPlanner + LLMRouter |
| 22–24 | Staged task execution + ReflectionEngine |
| 26 | Personalization bonus in ranking |
| 28 | Distributed inference design |
| 30 | Production-ready blueprint |

---

*Built with ❤️ by the FWG team — Autonomous Intelligence for the next generation of content.*
