from decimal import Decimal

from reconciliation_platform.anomaly.detector import detect_anomalies
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


def test_amount_mismatch_is_high_severity():
    decision = ReconciliationDecision(
        "B1", "I1", "REVIEW", "DETERMINISTIC_EXCEPTION", 0.5,
        "amount mismatch", ("exact_reference",), Decimal("10"), 0,
    )
    anomalies = detect_anomalies([decision])
    assert anomalies[0].anomaly_type == "AMOUNT_MISMATCH"
    assert anomalies[0].severity == "HIGH"


def test_unmatched_transaction_is_medium_severity():
    decision = ReconciliationDecision(
        "B1", None, "UNMATCHED", "NONE", 0.0,
        "none", (),
    )
    anomalies = detect_anomalies([decision])
    assert anomalies[0].anomaly_type == "UNMATCHED_TRANSACTION"
    assert anomalies[0].severity == "MEDIUM"
