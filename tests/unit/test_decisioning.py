from datetime import datetime, timezone

from reconciliation_platform.decisioning.review import build_review_cases
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


def test_review_case_id_is_deterministic():
    decision = ReconciliationDecision(
        "B1", "I1", "REVIEW", "DETERMINISTIC_EXCEPTION", 0.5,
        "amount mismatch", ("exact_reference",), amount_difference=10,
    )
    created_at = datetime(2026, 9, 20, tzinfo=timezone.utc)
    first = build_review_cases([decision], created_at=created_at)
    second = build_review_cases([decision], created_at=created_at)
    assert first == second
    assert first[0].case_id.startswith("REVIEW-")
