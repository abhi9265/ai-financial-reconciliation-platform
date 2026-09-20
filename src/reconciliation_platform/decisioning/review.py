"""Human-review decision contract."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    record_id: str
    candidate_record_id: str | None
    reason: str
    confidence: float
    created_at: datetime

def build_review_cases(decisions: list[ReconciliationDecision]) -> list[ReviewCase]:
    cases: list[ReviewCase] = []
    for d in decisions:
        if d.status == "REVIEW":
            cases.append(ReviewCase(
                case_id=f"REVIEW-{d.bank_record_id}",
                record_id=d.bank_record_id,
                candidate_record_id=d.counterparty_record_id,
                reason=d.explanation,
                confidence=d.confidence,
                created_at=datetime.now(timezone.utc),
            ))
    return cases
