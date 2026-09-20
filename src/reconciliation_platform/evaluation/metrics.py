"""Reconciliation evaluation metrics."""
from __future__ import annotations
from dataclasses import dataclass
from reconciliation_platform.reconciliation.engine import ReconciliationDecision

@dataclass(frozen=True)
class EvaluationMetrics:
    total: int
    matched: int
    review: int
    unmatched: int
    auto_match_rate: float

def evaluate(decisions: list[ReconciliationDecision]) -> EvaluationMetrics:
    total=len(decisions)
    matched=sum(d.status=="MATCHED" for d in decisions)
    review=sum(d.status=="REVIEW" for d in decisions)
    unmatched=sum(d.status=="UNMATCHED" for d in decisions)
    return EvaluationMetrics(total, matched, review, unmatched, matched/total if total else 0.0)
