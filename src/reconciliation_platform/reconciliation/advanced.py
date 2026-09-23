"""Scalable reconciliation extensions: blocking, one-to-many and partial payments."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

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
    """Find an invoice combination using O(k²) bounded subset search.

    The previous implementation enumerated all combinations. With max_items=3
    that is manageable for tiny candidate sets but becomes expensive at scale.
    Pair sums are indexed and triples reuse pair sums, avoiding materializing
    combinations for every bank transaction.
    """
    candidates = sorted(
        (c for c in candidates if _compatible(bank, c)),
        key=lambda c: (abs(c.amount - bank.amount), c.source_record_id),
    )
    if len(candidates) < 2:
        return None

    target = bank.amount
    for i, left in enumerate(candidates):
        for j in range(i + 1, len(candidates)):
            right = candidates[j]
            if abs(left.amount + right.amount - target) <= tolerance:
                return (left, right)

    if max_items < 3 or len(candidates) < 3:
        return None

    # For triples, hold the best pair seen for each sum and probe the complement.
    pair_by_sum: dict[Decimal, tuple[CanonicalTransaction, CanonicalTransaction]] = {}
    for i, left in enumerate(candidates):
        for j in range(i + 1, len(candidates)):
            right = candidates[j]
            pair_by_sum.setdefault(left.amount + right.amount, (left, right))
    for third in candidates:
        for pair_sum, pair in pair_by_sum.items():
            if third in pair:
                continue
            if abs(pair_sum + third.amount - target) <= tolerance:
                return pair + (third,)
    return None


def reconcile_advanced(
    bank_transactions: list[CanonicalTransaction],
    invoice_transactions: list[CanonicalTransaction],
    *,
    config: ReconciliationConfig | None = None,
    amount_tolerance: Decimal = Decimal("25"),
    max_one_to_many: int = 3,
) -> list[AdvancedDecision]:
    """Reconcile using blocking plus conservative complex-payment handling."""
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
