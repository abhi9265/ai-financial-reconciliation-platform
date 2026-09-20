"""Deterministic and fuzzy reconciliation engine."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from difflib import SequenceMatcher
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction

@dataclass(frozen=True)
class MatchCandidate:
    bank_record_id: str
    counterparty_record_id: str
    score: float
    signals: tuple[str, ...]
    amount_difference: Decimal
    date_difference_days: int

@dataclass(frozen=True)
class ReconciliationDecision:
    bank_record_id: str
    counterparty_record_id: str | None
    status: str
    tier: str
    confidence: float
    explanation: str
    signals: tuple[str, ...]
    amount_difference: Decimal | None = None
    date_difference_days: int | None = None

def _days(a: date, b: date) -> int:
    return abs((a - b).days)

def _name_similarity(a: str | None, b: str | None) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().replace(" ", ""), b.lower().replace(" ", "")).ratio()

def _candidate(bank: CanonicalTransaction, invoice: CanonicalTransaction) -> MatchCandidate:
    amount_diff = abs(bank.amount - invoice.amount)
    date_diff = _days(bank.transaction_date, invoice.transaction_date)
    signals: list[str] = []
    score = 0.0
    if bank.reference_number and invoice.invoice_number and bank.reference_number == invoice.invoice_number:
        signals.append("exact_reference")
        score += 0.55
    if amount_diff == 0:
        signals.append("exact_amount")
        score += 0.30
    elif amount_diff <= Decimal("1.00"):
        signals.append("near_amount")
        score += 0.20
    if date_diff == 0:
        signals.append("exact_date")
        score += 0.10
    elif date_diff <= 3:
        signals.append("date_within_3_days")
        score += 0.07
    name_score = _name_similarity(bank.counterparty_name, invoice.counterparty_name)
    if name_score >= 0.90:
        signals.append("counterparty_similarity")
        score += 0.05
    return MatchCandidate(bank.source_record_id, invoice.source_record_id, min(score, 1.0), tuple(signals), amount_diff, date_diff)

def reconcile(bank_transactions: list[CanonicalTransaction], invoice_transactions: list[CanonicalTransaction], *, date_tolerance_days: int = 3) -> list[ReconciliationDecision]:
    decisions: list[ReconciliationDecision] = []
    used: set[str] = set()
    for bank in bank_transactions:
        candidates = [_candidate(bank, inv) for inv in invoice_transactions if inv.source_record_id not in used]
        candidates.sort(key=lambda c: (c.score, -float(c.amount_difference), -c.date_difference_days), reverse=True)
        exact = [c for c in candidates if "exact_reference" in c.signals and "exact_amount" in c.signals and c.date_difference_days <= date_tolerance_days]
        if exact:
            c = exact[0]
            used.add(c.counterparty_record_id)
            decisions.append(ReconciliationDecision(bank.source_record_id, c.counterparty_record_id, "MATCHED", "DETERMINISTIC", 1.0, "Reference and amount agree; transaction date is within tolerance.", c.signals, c.amount_difference, c.date_difference_days))
            continue
        strong_ref = [c for c in candidates if "exact_reference" in c.signals]
        if strong_ref:
            c = strong_ref[0]
            decisions.append(ReconciliationDecision(bank.source_record_id, c.counterparty_record_id, "REVIEW", "DETERMINISTIC_EXCEPTION", c.score, "Reference identifies a candidate, but amount/date evidence does not satisfy the exact-match contract.", c.signals, c.amount_difference, c.date_difference_days))
            continue
        fuzzy = [c for c in candidates if c.score >= 0.70 and c.date_difference_days <= date_tolerance_days and c.amount_difference <= Decimal("1.00")]
        if fuzzy:
            c = fuzzy[0]
            if c.score >= 0.82:
                used.add(c.counterparty_record_id)
                decisions.append(ReconciliationDecision(bank.source_record_id, c.counterparty_record_id, "MATCHED", "FUZZY", c.score, "Multiple independent signals support the candidate.", c.signals, c.amount_difference, c.date_difference_days))
            else:
                decisions.append(ReconciliationDecision(bank.source_record_id, c.counterparty_record_id, "REVIEW", "FUZZY", c.score, "Candidate is plausible but below the configured auto-match confidence.", c.signals, c.amount_difference, c.date_difference_days))
            continue
        decisions.append(ReconciliationDecision(bank.source_record_id, None, "UNMATCHED", "NONE", 0.0, "No eligible counterparty record satisfied the matching rules.", tuple()))
    return decisions
