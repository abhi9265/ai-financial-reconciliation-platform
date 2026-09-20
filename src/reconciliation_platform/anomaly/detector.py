"""Anomaly classification from reconciliation decisions."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from reconciliation_platform.reconciliation.engine import ReconciliationDecision


@dataclass(frozen=True)
class Anomaly:
    record_id: str
    anomaly_type: str
    severity: str
    message: str
    amount_difference: Decimal | None = None


def detect_anomalies(decisions: list[ReconciliationDecision]) -> list[Anomaly]:
    anomalies: list[Anomaly] = []
    for decision in decisions:
        if decision.status == "REVIEW" and decision.amount_difference and decision.amount_difference > 1:
            anomalies.append(Anomaly(
                decision.bank_record_id,
                "AMOUNT_MISMATCH",
                "HIGH",
                "Bank amount differs from the referenced invoice.",
                decision.amount_difference,
            ))
        elif decision.status == "UNMATCHED":
            anomalies.append(Anomaly(
                decision.bank_record_id,
                "UNMATCHED_TRANSACTION",
                "MEDIUM",
                "No invoice candidate satisfied the reconciliation rules.",
            ))
    return anomalies
