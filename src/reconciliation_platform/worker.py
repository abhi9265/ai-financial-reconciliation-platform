"""Celery worker entrypoint for distributed reconciliation jobs."""
from __future__ import annotations

from celery import Celery

from reconciliation_platform.config import Settings
from reconciliation_platform.metrics import record_worker_job

settings = Settings.from_env()
celery_app = Celery("reconciliation_platform", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    task_time_limit=900,
    task_soft_time_limit=840,
    broker_connection_retry_on_startup=True,
)


@celery_app.task(
    name="reconciliation.process_job",
    bind=True,
    max_retries=3,
    acks_late=True,
    retry_backoff=True,
    retry_jitter=True,
)
def process_job(self, job_id: str, tenant_id: str, bank_key: str, purchase_key: str) -> None:
    from reconciliation_platform.api.app import _run_reconciliation_job

    try:
        _run_reconciliation_job(
            job_id,
            tenant_id,
            bank_key,
            purchase_key,
            raise_on_error=True,
        )
        record_worker_job("succeeded")
    except Exception as exc:
        record_worker_job("failed")
        raise self.retry(exc=exc) from exc
