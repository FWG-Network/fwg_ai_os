"""
backend/core/services.py
Central Service Hub — infrastructure clients + service imports.

Design:
  - Infrastructure clients (Redis, Qdrant) initialized here ONCE
  - Service singletons IMPORTED from their own modules (not re-created)
  - Lazy Qdrant collection setup
"""
from backend.core.config import settings
from backend.core.logger import log


# ── Infrastructure Clients ────────────────────────────────────────────
log.info("[Services] Initializing core infrastructure clients...")

# Redis
try:
    import redis as redis_lib
    # ✅ Fix: use REDIS_URL (consistent, not hardcoded port)
    redis_client = redis_lib.from_url(
        settings.REDIS_URL,
        db=0,
        decode_responses=True,
        socket_timeout=3,
    )
    redis_client.ping()
    log.info("✅ Redis client initialized")
except Exception as e:
    log.error(f"❌ Redis unavailable: {e}")
    redis_client = None

# Qdrant
try:
    from qdrant_client import QdrantClient
    qdrant_client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=5,
    )
    qdrant_client.get_collections()
    log.info("✅ Qdrant client initialized")
except Exception as e:
    log.error(f"❌ Qdrant unavailable: {e}")
    qdrant_client = None


# ── Service Singletons ────────────────────────────────────────────────
# ✅ Fix: IMPORT existing singletons — do NOT create new instances!
# Each module already creates its own singleton at bottom of file.
log.info("[Services] Importing service singletons...")

try:
    from backend.aios.task_planner     import task_planner_service
    from backend.aios.executor         import executor_service
    from backend.aios.reflection       import reflection_service
    from backend.aios.autonomous_loop  import autonomous_loop_service
    log.info("✅ AIOS services imported")
except Exception as e:
    log.error(f"❌ AIOS services failed: {e}")
    task_planner_service     = None
    executor_service         = None
    reflection_service       = None
    autonomous_loop_service  = None

try:
    from backend.services.discovery_engine      import discovery_engine_service
    from backend.services.ranking_engine        import ranking_engine_service
    from backend.services.personalization_engine import personalization_engine_service
    from backend.services.worker_client         import worker_client
    log.info("✅ Core services imported")
except Exception as e:
    log.error(f"❌ Core services failed: {e}")
    discovery_engine_service     = None
    ranking_engine_service       = None
    personalization_engine_service = None
    worker_client                = None

try:
    from backend.lim.orchestrator   import llm_orchestrator as llm_orchestrator_service
    from backend.lim.vector_memory  import vector_memory_service
    from backend.lim.rag_pipeline   import rag_pipeline
    log.info("✅ LIM services imported")
except Exception as e:
    log.error(f"❌ LIM services failed: {e}")
    llm_orchestrator_service = None
    vector_memory_service    = None
    rag_pipeline             = None

try:
    from backend.services.multimodal_engine import multimodal_engine_service
    log.info("✅ Multimodal service imported")
except Exception as e:
    log.warning(f"⚠️ Multimodal service unavailable: {e}")
    multimodal_engine_service = None

try:
    from backend.learning.reward        import reward_service
    from backend.learning.online_learning import online_learning_service
    from backend.learning.trainer       import trainer_service
    log.info("✅ Learning services imported")
except Exception as e:
    log.warning(f"⚠️ Learning services unavailable: {e}")
    reward_service          = None
    online_learning_service = None
    trainer_service         = None

log.info("[Services] ✅ All services ready")


# ── Qdrant Collection Setup (idempotent) ──────────────────────────────
def setup_vector_database() -> None:
    """Create default Qdrant collection if not exists."""
    if not qdrant_client:
        log.warning("[Services] Qdrant unavailable — skipping collection setup")
        return

    from qdrant_client.models import Distance, VectorParams
    collection = "aios_memory"

    try:
        existing = [c.name for c in qdrant_client.get_collections().collections]
        if collection not in existing:
            qdrant_client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
            log.info(f"✅ Qdrant collection '{collection}' created")
        else:
            log.info(f"✅ Qdrant collection '{collection}' exists")
    except Exception as e:
        log.error(f"❌ Qdrant setup error: {e}")


# ── Run setup (called from main.py lifespan, not on import) ──────────
# ✅ Fix: Don't auto-run on import — call from main.py startup
# setup_vector_database()  ← moved to backend/main.py lifespan
