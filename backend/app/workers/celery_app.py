from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "autoapplyai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

from kombu import Queue, Exchange

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    
    # Resilience & Operational Reliability
    task_acks_late=True, # Task is only acknowledged AFTER it finishes
    worker_prefetch_multiplier=1, # One task at a time per worker process
    task_reject_on_worker_lost=True, # Requeue if worker crashes
    
    # Queues & Routing
    task_default_queue='default',
    task_queues=(
        Queue('default', Exchange('default'), routing_key='default'),
        Queue('high_priority', Exchange('high_priority'), routing_key='high_priority'),
        Queue('dead_letter', Exchange('dead_letter'), routing_key='dead_letter'),
    ),
)
