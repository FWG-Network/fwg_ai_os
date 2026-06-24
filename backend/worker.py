from celery import Celery
from backend.core.config import settings

celery_app = Celery(
    "worker",
    broker=f"redis://{settings.REDIS_HOST}:6379/0",
    backend=f"redis://{settings.REDIS_HOST}:6379/0",
    include=["backend.learning.tasks"]
)

celery_app.conf.update(
    task_track_started=True,
)
