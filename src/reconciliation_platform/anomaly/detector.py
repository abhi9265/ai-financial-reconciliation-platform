"""Anomaly classification from reconciliation decisions and source data."""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

@dataclass(frozen=True)
class Anomaly:
    record_id: str
    anomaly_type: str
    severity: str
    message: str
    amount_difference: Decimal | None = None

def detect_anomalies(decisions: list[ReconciliationDecision], bank: list[CanonicalTransaction]) -> list[Anomaly]:
    by_id = {tx.source_record_id: tx for tx in bank}
    anomalies: list[Anomaly] = []
    for d in decisions:
        if d.status == "REVIEW" and d.amount_difference and d.amount_difference > 1:
            anomalies.append(Anomaly(d.bank_record_id, "AMOUNT_MISMATCH", "HIGH", "Bank amount differs from the referenced invoice.", d.amount_difference))
        elif d.status == "UNMATCHED":
            anomalies.append(Anomaly(d.bank_record_id, "UNMATCHED_TRANSACTION", "MEDIUM", "No invoice candidate satisfied the reconciliation rules."))
        tx = by_id[d.bank_record_id]
        if tx.source_system.value == "bank" and tx.amount_direction.value == "CREDIT" and tx.debit is None:
            pass
    return anomalies
