"""Lightweight process metrics for the MVP."""
from __future__ import annotations

from threading import Lock

_LOCK = Lock()
_COUNTERS = {
    "reconciliation_runs_total": 0,
    "reconciliation_matched_total": 0,
    "reconciliation_review_total": 0,
    "reconciliation_unmatched_total": 0,
    "reconciliation_failures_total": 0,
    "ai_reviews_total": 0,
}


def record_reconciliation(summary: dict, *, failed: bool = False) -> None:
    with _LOCK:
        _COUNTERS["reconciliation_runs_total"] += 1
        _COUNTERS["reconciliation_matched_total"] += int(summary.get("matched", 0))
        _COUNTERS["reconciliation_review_total"] += int(summary.get("review", 0))
        _COUNTERS["reconciliation_unmatched_total"] += int(summary.get("unmatched", 0))
        _COUNTERS["ai_reviews_total"] += int(summary.get("ai_review", {}).get("cases_reviewed", 0))
        if failed:
            _COUNTERS["reconciliation_failures_total"] += 1


def snapshot() -> dict[str, int]:
    with _LOCK:
        return dict(_COUNTERS)


def reset() -> None:
    with _LOCK:
        for key in _COUNTERS:
            _COUNTERS[key] = 0
