import torch
import gc

# ★★★ FIX: Critical performance optimizations for multi-process workers ★★★
try:
    torch.set_num_threads(1)
    print(f"AI-OS Worker: PyTorch thread count set to {torch.get_num_threads()}")
except Exception as e:
    print(f"Warning: Could not set torch thread count. {e}")

from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:6379/0",
    backend=f"redis://{settings.REDIS_HOST}:6379/0",
    include=[
        "backend.learning.tasks",
        "backend.aios.tasks",
        # Add other future task modules here
    ]
)
celery_app.conf.update(task_track_started=True)

# ★★★ FIX: Freeze GC after imports to preserve COW memory sharing ★★★
gc.freeze()
print("AI-OS Worker: Garbage Collector frozen. Ready for tasks.")
