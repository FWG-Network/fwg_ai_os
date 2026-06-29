"""
backend/worker.py
Celery Worker — async task processing.
Optimized for multi-process + PyTorch compatibility.
"""
import gc
from backend.core.logger import log

# ── PyTorch optimization (before Celery import) ───────────────────────
try:
    import torch
    torch.set_num_threads(1)
    log.info(f"[Worker] PyTorch threads: {torch.get_num_threads()}")
except ImportError:
    log.warning("[Worker] PyTorch not installed — skipping thread optimization")
except Exception as e:
    log.warning(f"[Worker] PyTorch thread config failed: {e}")

# ── Celery ────────────────────────────────────────────────────────────
from celery import Celery
from backend.core.config import settings

# ✅ Fix: use REDIS_URL — consistent, respects .env
_redis_url = settings.REDIS_URL

celery_app = Celery(
    "fwg_ai_os_worker",
    broker=f"{_redis_url}/1",      # db=1 for broker
    backend=f"{_redis_url}/1",     # db=1 for results
    include=[
        "backend.learning.tasks",  # feedback processing
        # "backend.aios.tasks",    # ← TODO: create when needed
    ]
)

celery_app.conf.update(
    task_track_started    = True,
    task_serializer       = "json",
    result_serializer     = "json",
    accept_content        = ["json"],
    timezone              = "UTC",
    task_acks_late        = True,   # ← requeue on worker crash
    worker_prefetch_multiplier = 1, # ← fair task distribution
)

# ── GC Freeze (COW memory sharing across processes) ───────────────────
gc.freeze()
log.info("[Worker] ✅ GC frozen — ready for tasks")
