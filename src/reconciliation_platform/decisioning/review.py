"""Deterministic human-review decision contract."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256

from reconciliation_platform.reconciliation.engine import ReconciliationDecision


@dataclass(frozen=True)
class ReviewCase:
    case_id: str
    record_id: str
    candidate_record_id: str | None
    reason: str
    confidence: float
    created_at: datetime


def build_review_cases(
    decisions: list[ReconciliationDecision],
    *,
    created_at: datetime | None = None,
) -> list[ReviewCase]:
    created_at = created_at or datetime.now(timezone.utc)
    cases: list[ReviewCase] = []
    for decision in decisions:
        if decision.status != "REVIEW":
            continue
        case_id = "REVIEW-" + sha256(
            f"{decision.bank_record_id}|{decision.counterparty_record_id or ''}|{decision.tier}".encode()
        ).hexdigest()[:16]
        cases.append(ReviewCase(
            case_id=case_id,
            record_id=decision.bank_record_id,
            candidate_record_id=decision.counterparty_record_id,
            reason=decision.explanation,
            confidence=decision.confidence,
            created_at=created_at,
        ))
    return cases
