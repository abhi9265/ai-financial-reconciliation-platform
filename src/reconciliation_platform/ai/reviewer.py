"""Provider-neutral AI escalation contract with safety validation.

The deterministic reconciliation engine remains authoritative. AI can only
produce a bounded recommendation for an already-escalated review case.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from reconciliation_platform.reconciliation.engine import ReconciliationDecision


ALLOWED_RECOMMENDATIONS = frozenset({"MATCH", "HUMAN_REVIEW", "UNMATCHED"})


@dataclass(frozen=True)
class AIReviewResult:
    recommendation: str
    confidence: float
    rationale: str
    model: str

    def __post_init__(self) -> None:
        if self.recommendation not in ALLOWED_RECOMMENDATIONS:
            raise ValueError(f"Unsupported AI recommendation: {self.recommendation!r}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("AI confidence must be between 0 and 1")
        if not self.rationale.strip():
            raise ValueError("AI rationale must not be empty")
        if not self.model.strip():
            raise ValueError("AI model must not be empty")


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


def validate_ai_result(result: AIReviewResult, decision: ReconciliationDecision) -> AIReviewResult:
    """Apply a conservative policy before an AI result can leave the adapter boundary.

    AI may recommend MATCH only when the deterministic engine already supplied a
    concrete candidate. Even then, the recommendation remains advisory and is
    never converted into an automatic reconciliation decision here.
    """
    if result.recommendation == "MATCH" and not decision.counterparty_record_id:
        return AIReviewResult(
            recommendation="HUMAN_REVIEW",
            confidence=min(result.confidence, 0.5),
            rationale="AI proposed MATCH without a deterministic candidate; routed to human review.",
            model=result.model,
        )
    return result


def escalate_reviews(
    decisions: list[ReconciliationDecision],
    reviewer: AIReviewer,
) -> dict[str, AIReviewResult]:
    """Review only deterministic REVIEW cases and validate provider output."""
    results: dict[str, AIReviewResult] = {}
    for decision in decisions:
        if decision.status != "REVIEW":
            continue
        results[decision.bank_record_id] = validate_ai_result(
            reviewer.review(decision), decision
        )
    return results
