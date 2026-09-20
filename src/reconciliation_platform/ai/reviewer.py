"""Provider-neutral AI escalation contract.

The core pipeline never requires an LLM. An AI provider can implement
AIReviewer and receive only an already-validated ambiguous case.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

@dataclass(frozen=True)
class AIReviewResult:
    recommendation: str
    confidence: float
    rationale: str
    model: str

class AIReviewer(Protocol):
    def review(self, decision: ReconciliationDecision) -> AIReviewResult: ...

class NoOpAIReviewer:
    """Safe default: never invent a match and always preserves human review."""

    def review(self, decision: ReconciliationDecision) -> AIReviewResult:
        return AIReviewResult(
            recommendation="HUMAN_REVIEW",
            confidence=0.0,
            rationale="No AI provider configured; deterministic evidence remains authoritative.",
            model="none",
        )

def escalate_reviews(decisions: list[ReconciliationDecision], reviewer: AIReviewer) -> dict[str, AIReviewResult]:
    return {
        d.bank_record_id: reviewer.review(d)
        for d in decisions
        if d.status == "REVIEW"
    }
