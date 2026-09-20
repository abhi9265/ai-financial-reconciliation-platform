"""Append-only decision audit records."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

@dataclass(frozen=True)
class DecisionAudit:
    record_id: str
    candidate_record_id: str | None
    status: str
    tier: str
    confidence: float
    explanation: str
    created_at: datetime

def to_audit_records(decisions: list[ReconciliationDecision]) -> list[DecisionAudit]:
    now=datetime.now(timezone.utc)
    return [
        DecisionAudit(d.bank_record_id,d.counterparty_record_id,d.status,d.tier,d.confidence,d.explanation,now)
        for d in decisions
    ]
