"""Scalable reconciliation extensions: blocking, one-to-many and partial payments."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, TransactionType
from reconciliation_platform.reconciliation.blocking import build_invoice_index, candidate_invoices
from reconciliation_platform.reconciliation.engine import ReconciliationConfig, _candidate


@dataclass(frozen=True)
class AdvancedDecision:
    bank_record_id: str
    counterparty_record_ids: tuple[str, ...]
    status: str
    relationship: str
    tier: str
    confidence: float
    amount_applied: Decimal
    amount_remaining: Decimal
    explanation: str
    candidate_count: int


def _compatible(bank: CanonicalTransaction, invoice: CanonicalTransaction) -> bool:
    return (
        (bank.transaction_type == TransactionType.PAYMENT and invoice.transaction_type == TransactionType.PURCHASE)
        or (bank.transaction_type == TransactionType.RECEIPT and invoice.transaction_type == TransactionType.SALE)
    )


def _subset_match(
    bank: CanonicalTransaction,
    candidates: list[CanonicalTransaction],
    *,
    tolerance: Decimal,
    max_items: int = 3,
) -> tuple[CanonicalTransaction, ...] | None:
    """Find a bounded invoice combination whose total equals the payment."""
    candidates = [c for c in candidates if _compatible(bank, c)]
    if len(candidates) < 2:
        return None

    bank_tokens = set(re.findall(r"[a-z0-9]+", (bank.counterparty_name or "").lower()))
    if bank_tokens:
        focused = [
            c for c in candidates
            if bank_tokens.intersection(
                re.findall(r"[a-z0-9]+", (c.counterparty_name or "").lower())
            )
        ]
        if len(focused) >= 2:
            candidates = focused

    candidates = sorted(candidates, key=lambda c: (abs(c.amount - bank.amount), c.source_record_id))
    pair_sums: dict[Decimal, tuple[int, int]] = {}

    if max_items >= 2:
        for i, left in enumerate(candidates):
            for j in range(i + 1, len(candidates)):
                right = candidates[j]
                total = left.amount + right.amount
                if abs(total - bank.amount) <= tolerance:
                    return (left, right)
                pair_sums.setdefault(total, (i, j))

    if max_items >= 3:
        for i, candidate in enumerate(candidates):
            target = bank.amount - candidate.amount
            for total, pair in pair_sums.items():
                if i in pair:
                    continue
                if abs(total - target) <= tolerance:
                    return tuple(candidates[k] for k in pair) + (candidate,)
    return None


def reconcile_advanced(
    bank_transactions: list[CanonicalTransaction],
    invoice_transactions: list[CanonicalTransaction],
    *,
    config: ReconciliationConfig | None = None,
    amount_tolerance: Decimal = Decimal("25"),
    max_one_to_many: int = 3,
) -> list[AdvancedDecision]:
    """Reconcile using blocking plus conservative complex-payment handling.

    Exact one-to-one matches are still delegated to the existing deterministic
    engine. Complex payments are only auto-matched when the allocation is
    unambiguous within the bounded candidate set. Partial payments remain
    explicitly represented instead of consuming the invoice prematurely.
    """
    config = config or ReconciliationConfig()
    used: set[str] = set()
    remaining: dict[str, Decimal] = {i.source_record_id: i.amount for i in invoice_transactions}
    decisions: list[AdvancedDecision] = []
    invoice_index = build_invoice_index(invoice_transactions)

    for bank in bank_transactions:
        candidates = candidate_invoices(
            bank,
            invoice_transactions,
            used=used,
            date_tolerance_days=max(config.date_tolerance_days, 7),
            amount_tolerance=amount_tolerance,
            index=invoice_index,
        )
        candidates = [c for c in candidates if _compatible(bank, c)]

        exact = [
            c for c in candidates
            if remaining[c.source_record_id] == bank.amount
            and c.invoice_number
            and bank.reference_number == c.invoice_number
        ]
        if exact:
            c = exact[0]
            used.add(c.source_record_id)
            remaining[c.source_record_id] = Decimal("0")
            decisions.append(AdvancedDecision(
                bank.source_record_id, (c.source_record_id,), "MATCHED", "ONE_TO_ONE",
                "DETERMINISTIC", 1.0, bank.amount, Decimal("0"),
                "Exact reference and remaining invoice amount agree.", len(candidates),
            ))
            continue

        subset = _subset_match(
            bank,
            [c for c in candidates if remaining[c.source_record_id] == c.amount],
            tolerance=amount_tolerance,
            max_items=max_one_to_many,
        )
        if subset:
            subset = tuple(sorted(subset, key=lambda x: x.source_record_id))
            ids = tuple(c.source_record_id for c in subset)
            for c in subset:
                used.add(c.source_record_id)
                remaining[c.source_record_id] = Decimal("0")
            decisions.append(AdvancedDecision(
                bank.source_record_id, ids, "MATCHED", "ONE_TO_MANY",
                "BLOCKED_SUBSET", 0.99, bank.amount, Decimal("0"),
                "Payment equals an unambiguous bounded combination of invoices.", len(candidates),
            ))
            continue

        partial_candidates = [
            c for c in candidates
            if Decimal("0") < remaining[c.source_record_id] > bank.amount
            and (
                bank.reference_number == c.invoice_number
                or (
                    bank.counterparty_name
                    and c.counterparty_name
                    and bank.counterparty_name.lower().replace(" ", "")
                    == c.counterparty_name.lower().replace(" ", "")
                )
            )
        ]
        if len(partial_candidates) == 1:
            c = partial_candidates[0]
            applied = bank.amount
            remaining[c.source_record_id] -= applied
            decisions.append(AdvancedDecision(
                bank.source_record_id, (c.source_record_id,), "MATCHED", "PARTIAL_PAYMENT",
                "DETERMINISTIC", 0.95, applied, remaining[c.source_record_id],
                "Payment is allocated against a uniquely identified invoice without consuming it until fully paid.",
                len(candidates),
            ))
            if remaining[c.source_record_id] == 0:
                used.add(c.source_record_id)
            continue

        scored = sorted((_candidate(bank, c, config) for c in candidates), key=lambda x: x.score, reverse=True)
        if scored and scored[0].score >= config.fuzzy_review_threshold:
            c = scored[0]
            decisions.append(AdvancedDecision(
                bank.source_record_id, (c.counterparty_record_id,), "REVIEW", "AMBIGUOUS",
                "FUZZY", c.score, Decimal("0"), bank.amount,
                "Candidate exists but the evidence is insufficient for automatic allocation.", len(candidates),
            ))
        else:
            decisions.append(AdvancedDecision(
                bank.source_record_id, tuple(), "UNMATCHED", "NONE", "NONE",
                0.0, Decimal("0"), bank.amount,
                "No eligible blocked candidate satisfied the complex matching contract.", len(candidates),
            ))
    return decisions
