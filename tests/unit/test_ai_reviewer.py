from decimal import Decimal

import pytest

from reconciliation_platform.ai.reviewer import (
    AIReviewResult,
    NoOpAIReviewer,
    escalate_reviews,
)
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


def decision(*, status: str = "REVIEW", candidate: str | None = "I1") -> ReconciliationDecision:
    return ReconciliationDecision(
        bank_record_id="B1",
        counterparty_record_id=candidate,
        status=status,
        tier="FUZZY",
        confidence=0.72,
        explanation="Ambiguous candidate requires review.",
        signals=("counterparty_similarity",),
        amount_difference=Decimal("7.50"),
        date_difference_days=1,
    )


class FakeReviewer:
    def __init__(self, result: AIReviewResult) -> None:
        self.result = result
        self.calls = 0

    def review(self, decision: ReconciliationDecision) -> AIReviewResult:
        self.calls += 1
        return self.result


def test_noop_reviewer_preserves_human_review() -> None:
    result = NoOpAIReviewer().review(decision())
    assert result.recommendation == "HUMAN_REVIEW"
    assert result.confidence == 0.0


def test_escalation_reviews_only_review_cases() -> None:
    reviewer = FakeReviewer(AIReviewResult("HUMAN_REVIEW", 0.4, "Needs accountant review.", "test-model"))
    results = escalate_reviews([decision(), decision(status="MATCHED")], reviewer)
    assert list(results) == ["B1"]
    assert reviewer.calls == 1


def test_invalid_recommendation_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unsupported AI recommendation"):
        AIReviewResult("AUTO_APPROVE", 0.9, "bad", "test-model")


def test_match_without_deterministic_candidate_is_downgraded() -> None:
    reviewer = FakeReviewer(AIReviewResult("MATCH", 0.99, "Looks similar.", "test-model"))
    result = escalate_reviews([decision(candidate=None)], reviewer)["B1"]
    assert result.recommendation == "HUMAN_REVIEW"
    assert result.confidence <= 0.5
    assert "deterministic candidate" in result.rationale


def test_confidence_and_rationale_are_validated() -> None:
    with pytest.raises(ValueError):
        AIReviewResult("MATCH", 1.1, "rationale", "model")
    with pytest.raises(ValueError):
        AIReviewResult("MATCH", 0.5, " ", "model")
