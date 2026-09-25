"""Prometheus metrics for API, reconciliation and worker operations."""
from __future__ import annotations

from threading import Lock

from prometheus_client import Counter, Gauge, Histogram, generate_latest

_LOCK = Lock()
_COUNTERS = {
    "reconciliation_runs_total": 0,
    "reconciliation_matched_total": 0,
    "reconciliation_review_total": 0,
    "reconciliation_unmatched_total": 0,
    "reconciliation_failures_total": 0,
    "ai_reviews_total": 0,
}

REQUESTS = Counter(
    "reconciliation_http_requests_total",
    "Total HTTP requests.",
    ["method", "path", "status_class"],
)
REQUEST_LATENCY = Histogram(
    "reconciliation_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
RECONCILIATIONS = Counter(
    "reconciliation_jobs_total",
    "Completed reconciliation jobs.",
    ["mode", "status"],
)
MATCHED = Counter(
    "reconciliation_decisions_total",
    "Reconciliation decisions by outcome.",
    ["outcome"],
)
JOB_DURATION = Histogram(
    "reconciliation_job_duration_seconds",
    "End-to-end reconciliation job duration.",
    ["mode"],
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 300, 900),
)
AI_REVIEWS = Counter(
    "reconciliation_ai_reviews_total",
    "AI review cases processed.",
    ["provider", "recommendation"],
)
AI_FAILURES = Counter(
    "reconciliation_ai_failures_total",
    "AI review/provider failures.",
    ["provider"],
)
QUEUE_DEPTH = Gauge(
    "reconciliation_queue_depth",
    "Known queued reconciliation jobs.",
)
REVIEW_BACKLOG = Gauge(
    "reconciliation_review_backlog",
    "Persisted review cases awaiting downstream human action.",
)
WORKER_JOBS = Counter(
    "reconciliation_worker_jobs_total",
    "Celery worker job outcomes.",
    ["status"],
)


def observe_http(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    REQUESTS.labels(method=method, path=path, status_class=f"{status_code // 100}xx").inc()
    REQUEST_LATENCY.labels(method=method, path=path).observe(duration_seconds)


def record_reconciliation(summary: dict, *, failed: bool = False, mode: str = "sync", duration_seconds: float | None = None) -> None:
    status = "failed" if failed else "succeeded"
    RECONCILIATIONS.labels(mode=mode, status=status).inc()
    if duration_seconds is not None:
        JOB_DURATION.labels(mode=mode).observe(duration_seconds)
    with _LOCK:
        _COUNTERS["reconciliation_runs_total"] += 1
        _COUNTERS["reconciliation_matched_total"] += int(summary.get("matched", 0))
        _COUNTERS["reconciliation_review_total"] += int(summary.get("review", 0))
        _COUNTERS["reconciliation_unmatched_total"] += int(summary.get("unmatched", 0))
        _COUNTERS["ai_reviews_total"] += int(summary.get("ai_review", {}).get("cases_reviewed", 0))
        if failed:
            _COUNTERS["reconciliation_failures_total"] += 1
    for outcome, key in (("matched", "matched"), ("review", "review"), ("unmatched", "unmatched")):
        count = int(summary.get(key, 0))
        if count:
            MATCHED.labels(outcome=outcome).inc(count)


def record_ai_review(provider: str, recommendation: str) -> None:
    AI_REVIEWS.labels(provider=provider, recommendation=recommendation).inc()


def record_ai_failure(provider: str) -> None:
    AI_FAILURES.labels(provider=provider).inc()


def set_queue_depth(depth: int) -> None:
    QUEUE_DEPTH.set(max(0, depth))


def set_review_backlog(depth: int) -> None:
    REVIEW_BACKLOG.set(max(0, depth))


def record_worker_job(status: str) -> None:
    WORKER_JOBS.labels(status=status).inc()


def prometheus_payload() -> bytes:
    return generate_latest()


def snapshot() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)


def reset() -> None:
    with _LOCK:
        for key in _COUNTERS:
            _COUNTERS[key] = 0
