from pathlib import Path

import pytest

from reconciliation_platform.ai.reviewer import NoOpAIReviewer, escalate_reviews
from reconciliation_platform.evaluation.metrics import (
    evaluate,
    evaluate_against_ground_truth,
    load_ground_truth,
)
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


def test_ai_escalation_is_safe_by_default():
    d = ReconciliationDecision(
        "B1", "I1", "REVIEW", "DETERMINISTIC_EXCEPTION", 0.5, "amount mismatch", ("exact_reference",)
    )
    result = escalate_reviews([d], NoOpAIReviewer())["B1"]
    assert result.recommendation == "HUMAN_REVIEW"
    assert result.model == "none"


def test_evaluation_metrics():
    ds = [
        ReconciliationDecision("B1", "I1", "MATCHED", "DETERMINISTIC", 1.0, "ok", ()),
        ReconciliationDecision("B2", "I2", "REVIEW", "FUZZY", 0.7, "review", ()),
        ReconciliationDecision("B3", None, "UNMATCHED", "NONE", 0.0, "none", ()),
    ]
    m = evaluate(ds)
    assert (m.total, m.matched, m.review, m.unmatched) == (3, 1, 1, 1)
    assert m.auto_match_rate == 1 / 3


def test_ground_truth_evaluation_distinguishes_safe_review_from_false_match():
    decisions = [
        ReconciliationDecision("B1", "I1", "MATCHED", "FUZZY", 0.9, "ok", ()),
        ReconciliationDecision("B2", "I2", "REVIEW", "FUZZY", 0.7, "ambiguous", ()),
        ReconciliationDecision("B3", None, "UNMATCHED", "NONE", 0.0, "missing", ()),
    ]
    truth = [
        {"bank_transaction_id": "B1", "invoice_record_id": "I1", "relationship": "MATCH", "defect_type": ""},
        {"bank_transaction_id": "B2", "invoice_record_id": "I2", "relationship": "UNMATCHED", "defect_type": "AMOUNT_MISMATCH"},
        {"bank_transaction_id": "B3", "invoice_record_id": "I3", "relationship": "UNMATCHED", "defect_type": "MISSING_INVOICE"},
    ]

    m = evaluate_against_ground_truth(decisions, truth)

    assert m.total == 3
    assert m.correct_auto_matches == 1
    assert m.false_auto_matches == 0
    assert m.missed_matches == 0
    assert m.review_on_actual_unmatched == 1
    assert m.exception_capture_rate == 1.0
    assert m.match_precision == 1.0
    assert m.match_recall == 1.0
    assert m.pair_accuracy == 1.0


def test_ground_truth_evaluation_flags_false_auto_match():
    decisions = [
        ReconciliationDecision("B1", "I1", "MATCHED", "FUZZY", 0.9, "ok", ()),
        ReconciliationDecision("B2", "I2", "MATCHED", "FUZZY", 0.9, "incorrect", ()),
        ReconciliationDecision("B3", None, "UNMATCHED", "NONE", 0.0, "missing", ()),
    ]
    truth = [
        {"bank_transaction_id": "B1", "invoice_record_id": "I1", "relationship": "MATCH", "defect_type": ""},
        {"bank_transaction_id": "B2", "invoice_record_id": "I2", "relationship": "UNMATCHED", "defect_type": "AMOUNT_MISMATCH"},
        {"bank_transaction_id": "B3", "invoice_record_id": "I3", "relationship": "UNMATCHED", "defect_type": "MISSING_INVOICE"},
    ]

    metrics = evaluate_against_ground_truth(decisions, truth)

    assert metrics.correct_auto_matches == 1
    assert metrics.false_auto_matches == 1
    assert metrics.match_precision == 0.5
    assert metrics.match_recall == 1.0
    assert metrics.false_positive_rate == 0.5
    assert metrics.exception_capture_rate == 1.0


def test_ground_truth_loader_validates_duplicate_ids():
    path = Path("data/synthetic/seed/ground_truth.csv")
    rows = load_ground_truth(path)
    assert len(rows) == 100
    assert sum(row["relationship"] == "MATCH" for row in rows) == 90
    assert sum(row["relationship"] == "UNMATCHED" for row in rows) == 10

    with pytest.raises(ValueError, match="duplicate"):
        evaluate_against_ground_truth(
            [
                ReconciliationDecision("B1", "I1", "MATCHED", "DETERMINISTIC", 1.0, "ok", ()),
                ReconciliationDecision("B1", "I2", "MATCHED", "DETERMINISTIC", 1.0, "ok", ()),
            ],
            [{"bank_transaction_id": "B1", "invoice_record_id": "I1", "relationship": "MATCH", "defect_type": ""}],
        )
