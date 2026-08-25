"""Celery app for async document generation.

Broker + result backend both point to Redis (REDIS_URL).
Tasks live in app.tasks.document_tasks.
"""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "n2o_dvr",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.document_tasks"],
)

celery_app.conf.update(
    # The Starter worker has 512 MB. Keep heavy document dependencies lazy and
    # run one child so pythermalcomfort is retained by only that child instead
    # of the parent plus two prefork processes.
    worker_concurrency=1,
    task_track_started=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_time_limit=60 * 20,  # hard limit 20 min
    task_soft_time_limit=60 * 15,
    worker_max_tasks_per_child=50,
)
