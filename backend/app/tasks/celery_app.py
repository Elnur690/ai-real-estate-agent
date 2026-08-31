from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "realestate_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.jobs"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Baku",
    enable_utc=True,
    beat_schedule={
        "scrape-and-match-continuous-30s": {
            "task": "app.tasks.jobs.run_scheduled_ingestion",
            "schedule": 30.0,  # Real-time: 30 seconds
        },
        "check-plan-expirations-daily": {
            "task": "app.tasks.jobs.check_plan_expirations",
            "schedule": 86400.0,  # 24 hours
        },
        "perform-database-backup-daily": {
            "task": "app.tasks.jobs.perform_database_backup",
            "schedule": 86400.0,  # 24 hours
        }
    }
)

# Explicitly import jobs to ensure tasks are registered in all worker environments
import app.tasks.jobs  # noqa: F401, E402
