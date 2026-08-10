from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "realestate_tasks",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Baku",
    enable_utc=True,
    beat_schedule={
        "scrape-and-match-every-15-min": {
            "task": "app.tasks.jobs.run_scheduled_ingestion",
            "schedule": 900.0,  # 15 minutes
        },
        "check-plan-expirations-daily": {
            "task": "app.tasks.jobs.check_plan_expirations",
            "schedule": 86400.0,  # 24 hours
        }
    }
)
