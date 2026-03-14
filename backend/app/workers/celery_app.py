"""Celery application setup."""
from __future__ import annotations
from celery import Celery
from app.config import get_settings
settings = get_settings()
celery_app = Celery(
    "contentflow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_routes={"app.workers.tasks.distribute_post": {"queue": "distribution"}},
)
