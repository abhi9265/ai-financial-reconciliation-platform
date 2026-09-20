"""Ground-truth evaluation for reconciliation decisions."""
from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from reconciliation_platform.reconciliation.engine import ReconciliationDecision


@dataclass(frozen=True)
class EvaluationMetrics:
    total: int
    matched: int
    review: int
    unmatched: int
    auto_match_rate: float


@dataclass(frozen=True)
class GroundTruthMetrics:
    total: int
    actual_matches: int
    actual_unmatched: int
    correct_auto_matches: int
    false_auto_matches: int
    missed_matches: int
    review_on_actual_unmatched: int
    unresolved_actual_unmatched: int
    match_precision: float
    match_recall: float
    match_f1: float
    false_positive_rate: float
    exception_capture_rate: float
    pair_accuracy: float


def evaluate(decisions: Iterable[ReconciliationDecision]) -> EvaluationMetrics:
    decisions = list(decisions)
    total = len(decisions)
    matched = sum(d.status == "MATCHED" for d in decisions)
    review = sum(d.status == "REVIEW" for d in decisions)
    unmatched = sum(d.status == "UNMATCHED" for d in decisions)
    return EvaluationMetrics(total, matched, review, unmatched, matched / total if total else 0.0)


def load_ground_truth(path: str | Path) -> list[dict[str, str]]:
    """Load and validate the benchmark's bank-to-invoice relationships."""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    required = {"bank_transaction_id", "invoice_record_id", "relationship", "defect_type"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("ground truth must contain the required relationship columns")

    seen: set[str] = set()
    for row in rows:
        bank_id = row["bank_transaction_id"]
        if bank_id in seen:
            raise ValueError(f"duplicate ground-truth bank transaction: {bank_id}")
        seen.add(bank_id)
        if row["relationship"] not in {"MATCH", "UNMATCHED"}:
            raise ValueError(f"unsupported ground-truth relationship: {row['relationship']}")
    return rows


def evaluate_against_ground_truth(
    decisions: Iterable[ReconciliationDecision],
    ground_truth: Iterable[Mapping[str, str]],
) -> GroundTruthMetrics:
    """Compare auto-match behavior with labeled relationships.

    REVIEW is treated as unresolved rather than as an automatic match. This
    preserves the distinction between safe escalation and a false match.
    """
    decisions = list(decisions)
    truth = list(ground_truth)
    decisions_by_bank = {d.bank_record_id: d for d in decisions}
    truth_by_bank = {row["bank_transaction_id"]: row for row in truth}

    if len(decisions_by_bank) != len(decisions):
        raise ValueError("duplicate decision bank record IDs are not allowed")
    if len(truth_by_bank) != len(truth):
        raise ValueError("duplicate ground-truth bank record IDs are not allowed")
    if set(decisions_by_bank) != set(truth_by_bank):
        missing = sorted(set(truth_by_bank) - set(decisions_by_bank))
        extra = sorted(set(decisions_by_bank) - set(truth_by_bank))
        raise ValueError(f"decision/ground-truth IDs differ; missing={missing}, extra={extra}")

    total = len(truth_by_bank)
    actual_matches = sum(row["relationship"] == "MATCH" for row in truth_by_bank.values())
    actual_unmatched = total - actual_matches

    correct_auto_matches = 0
    false_auto_matches = 0
    missed_matches = 0
    review_on_actual_unmatched = 0
    unresolved_actual_unmatched = 0
    pair_correct = 0

    for bank_id, row in truth_by_bank.items():
        decision = decisions_by_bank[bank_id]
        actual_match = row["relationship"] == "MATCH"

        if actual_match:
            if decision.status == "MATCHED":
                correct_auto_matches += 1
                if decision.counterparty_record_id == row["invoice_record_id"]:
                    pair_correct += 1
            else:
                missed_matches += 1
        elif decision.status == "MATCHED":
            false_auto_matches += 1
        else:
            unresolved_actual_unmatched += 1
            if decision.status == "REVIEW":
                review_on_actual_unmatched += 1

    precision = (
        correct_auto_matches / (correct_auto_matches + false_auto_matches)
        if correct_auto_matches + false_auto_matches
        else 0.0
    )
    recall = correct_auto_matches / actual_matches if actual_matches else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    false_positive_rate = false_auto_matches / actual_unmatched if actual_unmatched else 0.0
    exception_capture_rate = (
        unresolved_actual_unmatched / actual_unmatched if actual_unmatched else 0.0
    )
    pair_accuracy = pair_correct / actual_matches if actual_matches else 0.0

    return GroundTruthMetrics(
        total=total,
        actual_matches=actual_matches,
        actual_unmatched=actual_unmatched,
        correct_auto_matches=correct_auto_matches,
        false_auto_matches=false_auto_matches,
        missed_matches=missed_matches,
        review_on_actual_unmatched=review_on_actual_unmatched,
        unresolved_actual_unmatched=unresolved_actual_unmatched,
        match_precision=precision,
        match_recall=recall,
        match_f1=f1,
        false_positive_rate=false_positive_rate,
        exception_capture_rate=exception_capture_rate,
        pair_accuracy=pair_accuracy,
    )
