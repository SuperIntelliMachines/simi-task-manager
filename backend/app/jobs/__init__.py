from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("atm_worker", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    "generate-daily-policy-reminders": {
        "task": "run_daily_policy_reminder_cycle",
        "schedule": crontab(hour=0, minute=0),
    },
    "process-renewal-escalations-daily": {
        "task": "process_renewal_escalations",
        "schedule": crontab(hour=1, minute=0),
    },
    "process-due-policy-reminders-every-5-minutes": {
        "task": "process_due_policy_reminders",
        "schedule": crontab(minute="*/5"),
    },
    "process-due-reminders-every-5-minutes": {
        "task": "process_due_reminders",
        "schedule": crontab(minute="*/5"),
    },
}
celery_app.conf.timezone = "UTC"

# Register task modules with the worker.
celery_app.autodiscover_tasks(["app.jobs"])

from app.jobs import celery_tasks as _celery_tasks  # noqa: E402, F401
