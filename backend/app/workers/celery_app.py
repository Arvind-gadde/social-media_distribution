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
    include=["app.workers.tasks", "app.workers.billing_tasks"],
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
        "app.workers.tasks.expire_stale_approvals": {"queue": "default"},
        "app.workers.tasks.check_goals":           {"queue": "default"},
        "app.workers.tasks.monitor_competitors":   {"queue": "agent"},
        "app.workers.tasks.sync_analytics":        {"queue": "agent"},
        "app.workers.tasks.run_token_refresh":     {"queue": "default"},
        "app.workers.tasks.run_agent_orchestrator": {"queue": "agent"},
        "app.workers.tasks.sync_all_inboxes":      {"queue": "agent"},
        "app.workers.tasks.evaluate_dms":          {"queue": "agent"},
        "app.workers.tasks.scan_niche_trends":     {"queue": "agent"},
        "app.workers.tasks.dispatch_trend_insights": {"queue": "agent"},
        "app.workers.tasks.send_expo_push":        {"queue": "default"},
        "app.workers.tasks.sync_all_stripe_customers": {"queue": "default"},
        "app.workers.tasks.handle_subscription_expiry": {"queue": "default"},
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
        "expire-stale-approvals": {
            "task": "app.workers.tasks.expire_stale_approvals",
            "schedule": crontab(minute=30),  # once per hour at :30
        },
        "check-goal-progress": {
            "task": "app.workers.tasks.check_goals",
            "schedule": crontab(minute=30, hour=8),  # daily at 8:00 AM
        },
        "monitor-competitors": {
            "task": "app.workers.tasks.monitor_competitors",
            "schedule": crontab(minute=0, hour=6),  # daily at 6:00 AM
        },
        "sync-analytics": {
            "task": "app.workers.tasks.sync_analytics",
            "schedule": crontab(minute=15, hour="*/4"),  # every 4 hours at :15
        },
        "refresh-expiring-tokens": {
            "task": "app.workers.tasks.run_token_refresh",
            "schedule": crontab(minute=0, hour=3),  # daily at 3:00 AM
        },
        "run-agent-orchestrator": {
            "task": "app.workers.tasks.run_agent_orchestrator",
            "schedule": crontab(minute=0, hour="*/6"),  # every 6 hours
        },
        "sync-dm-inboxes": {
            "task": "app.workers.tasks.sync_all_inboxes",
            "schedule": crontab(minute=0),  # every hour
        },
        "evaluate-dms": {
            "task": "app.workers.tasks.evaluate_dms",
            "schedule": crontab(minute=30),  # every hour at :30
        },
        "scan-niche-trends": {
            "task": "app.workers.tasks.scan_niche_trends",
            "schedule": crontab(minute=0, hour="*/4"),  # every 4 hours
        },
        # Phase 11: SaaS billing safety nets (defined in app.workers.billing_tasks)
        "sync-all-stripe-customers": {
            "task": "app.workers.tasks.sync_all_stripe_customers",
            "schedule": crontab(minute=0, hour=3),  # daily at 3:00 AM — heal missed webhooks
        },
        "handle-subscription-expiry": {
            "task": "app.workers.tasks.handle_subscription_expiry",
            "schedule": crontab(minute=0),  # hourly — downgrade expired subs
        },
    },
)
