"""
FinVoice — Celery App Configuration & Async Tasks
"""

import os

try:
    from celery import Celery
    from celery.schedules import crontab

    # Lazy config — avoid importing config.py at module level
    # to prevent circular imports when used outside FastAPI context
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    celery_app = Celery(
        "finvoice",
        broker=REDIS_URL,
        backend=REDIS_URL,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kolkata",
        enable_utc=True,
        beat_schedule={
            # Daily portfolio drift check at 11 PM IST
            "daily-drift-detection": {
                "task": "tasks.daily_drift.check_all_portfolios",
                "schedule": crontab(hour=17, minute=30),  # 11 PM IST = 5:30 PM UTC
            },
            # Weekly model retraining on Sunday at 2 AM IST
            "weekly-model-retrain": {
                "task": "tasks.retrain_models.retrain_all",
                "schedule": crontab(day_of_week=0, hour=20, minute=30),
            },
        },
    )

except ImportError:
    # Celery not installed or Redis not available — create a dummy
    # so the file can be imported without crashing the main app
    class _DummyCelery:
        def task(self, *a, **kw):
            def decorator(func):
                return func
            return decorator

    celery_app = _DummyCelery()
