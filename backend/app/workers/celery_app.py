"""Celery application setup with beat schedule."""
from __future__ import annotations
from celery import Celery
from celery.schedules import crontab
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
    task_routes={
        "app.workers.tasks.distribute_post":       {"queue": "distribution"},
        "app.workers.tasks.run_content_agent":     {"queue": "agent"},
        "app.workers.tasks.process_publish_jobs":  {"queue": "distribution"},
        "app.workers.tasks.process_outbox":        {"queue": "default"},
        "app.workers.tasks.sync_analytics":        {"queue": "agent"},
        "app.workers.tasks.run_token_refresh":     {"queue": "default"},
        "app.workers.tasks.send_expo_push":        {"queue": "default"},
    },
    beat_schedule={
        "collect-and-process-content": {
            "task": "app.workers.tasks.run_content_agent",
            "schedule": crontab(minute=0, hour="*/2"),  # every 2 hours
        },
        "process-publish-jobs": {
            "task": "app.workers.tasks.process_publish_jobs",
            "schedule": crontab(minute="*/5"),  # every 5 minutes
        },
        "process-outbox-events": {
            "task": "app.workers.tasks.process_outbox",
            "schedule": crontab(minute="*/2"),  # every 2 minutes
        },
        "sync-analytics": {
            "task": "app.workers.tasks.sync_analytics",
            "schedule": crontab(minute=15, hour="*/4"),  # every 4 hours at :15
        },
        "refresh-expiring-tokens": {
            "task": "app.workers.tasks.run_token_refresh",
            "schedule": crontab(minute=0, hour=3),  # daily at 3:00 AM
        },
    },
)
