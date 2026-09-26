from reconciliation_platform.metrics import (
    observe_http,
    prometheus_payload,
    record_ai_review,
    record_reconciliation,
    record_worker_job,
    reset,
    set_queue_depth,
    set_review_backlog,
    snapshot,
)
from reconciliation_platform.observability import get_request_id, set_request_id


def test_prometheus_metrics_and_snapshot():
    reset()
    record_reconciliation(
        {"matched": 2, "review": 1, "unmatched": 3, "ai_review": {"cases_reviewed": 1}},
        mode="async",
    )
    observe_http("GET", "/health", 200, 0.01)
    record_ai_review("none", "REVIEW")
    record_worker_job("succeeded")
    set_queue_depth(4)
    set_review_backlog(2)

    snap = snapshot()
    assert snap["reconciliation_runs_total"] == 1
    assert snap["reconciliation_matched_total"] == 2
    assert snap["reconciliation_review_total"] == 1
    assert snap["reconciliation_unmatched_total"] == 3

    payload = prometheus_payload().decode()
    assert "reconciliation_http_requests_total" in payload
    assert "reconciliation_jobs_total" in payload
    assert "reconciliation_ai_reviews_total" in payload
    assert "reconciliation_queue_depth" in payload


def test_request_id_context():
    request_id = set_request_id("observability-test")
    assert request_id == "observability-test"
    assert get_request_id() == "observability-test"
