import os

from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

app = Celery("pchub")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "check-computer-heartbeats": {
        "task": "apps.computers.tasks.check_computer_heartbeats",
        "schedule": 60.0,  # Run every 60 seconds
    },
    "cleanup-old-metrics": {
        "task": "apps.computers.tasks.cleanup_old_metrics",
        "schedule": 86400.0,  # Run daily (24 hours)
    },
    "enforce-subscriptions": {
        "task": "apps.clubs.tasks.enforce_subscriptions",
        "schedule": 3600.0,  # Hourly: expire trials, block overdue debts
    },
    "process-booking-lifecycle": {
        "task": "apps.bookings.tasks.process_booking_lifecycle",
        "schedule": 60.0,  # Every minute: expire no-shows, free PCs before bookings
    },
    "sync-game-versions": {
        "task": "apps.games.tasks.sync_game_versions",
        "schedule": 300.0,  # Every 5 min: auto-queue game updates to idle PCs
    },
}

app.conf.enable_utc = True
app.conf.timezone = "Asia/Tashkent"

app.conf.task_routes = {}

app.conf.task_default_retry_delay = 60
app.conf.task_max_retries = 3

app.conf.task_annotations = {}


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
