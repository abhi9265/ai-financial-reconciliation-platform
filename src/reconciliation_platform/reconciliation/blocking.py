"""Candidate blocking for scalable reconciliation.

Blocking reduces the expensive matching surface before fuzzy scoring. It is an
optimization and a safety boundary: a record that cannot satisfy the coarse
candidate contract is never considered by the more expensive matcher.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return "".join(_TOKEN_RE.findall(value.lower()))


def name_tokens(value: str | None) -> frozenset[str]:
    if not value:
        return frozenset()
    return frozenset(_TOKEN_RE.findall(value.lower()))


def amount_bucket(amount: Decimal, bucket_size: Decimal = Decimal("100")) -> int:
    return int(amount // bucket_size)


@dataclass(frozen=True)
class InvoiceBlockIndex:
    """Reusable inverted indexes for candidate generation.

    The previous implementation scanned every invoice for every bank row,
    making candidate generation O(bank_rows * invoice_rows). This index keeps
    the same permissive blocking contract while making lookup proportional to
    the relevant amount buckets/names/tokens.
    """

    invoices_by_id: dict[str, CanonicalTransaction]
    by_amount_bucket: dict[int, tuple[str, ...]]
    by_normalized_name: dict[str, tuple[str, ...]]
    by_token: dict[str, tuple[str, ...]]


def build_invoice_blocks(
    invoices: Iterable[CanonicalTransaction],
    *,
    amount_bucket_size: Decimal = Decimal("100"),
) -> dict[tuple[int, str], list[CanonicalTransaction]]:
    blocks: dict[tuple[int, str], list[CanonicalTransaction]] = defaultdict(list)
    for invoice in invoices:
        blocks[(amount_bucket(invoice.amount, amount_bucket_size), normalize_name(invoice.counterparty_name))].append(invoice)
    return dict(blocks)


def build_invoice_index(
    invoices: Iterable[CanonicalTransaction],
    *,
    amount_bucket_size: Decimal = Decimal("100"),
) -> InvoiceBlockIndex:
    """Build deterministic inverted indexes once per reconciliation batch."""
    invoices_by_id: dict[str, CanonicalTransaction] = {}
    amount_blocks: dict[int, list[str]] = defaultdict(list)
    name_blocks: dict[str, list[str]] = defaultdict(list)
    token_blocks: dict[str, list[str]] = defaultdict(list)

    for invoice in invoices:
        record_id = invoice.source_record_id
        invoices_by_id[record_id] = invoice
        amount_blocks[amount_bucket(invoice.amount, amount_bucket_size)].append(record_id)

        normalized = normalize_name(invoice.counterparty_name)
        if normalized:
            name_blocks[normalized].append(record_id)

        for token in name_tokens(invoice.counterparty_name):
            token_blocks[token].append(record_id)

    return InvoiceBlockIndex(
        invoices_by_id=invoices_by_id,
        by_amount_bucket={k: tuple(v) for k, v in amount_blocks.items()},
        by_normalized_name={k: tuple(v) for k, v in name_blocks.items()},
        by_token={k: tuple(v) for k, v in token_blocks.items()},
    )


def candidate_invoices(
    bank: CanonicalTransaction,
    invoices: list[CanonicalTransaction],
    *,
    used: set[str] | None = None,
    date_tolerance_days: int = 7,
    amount_tolerance: Decimal = Decimal("25"),
    amount_bucket_size: Decimal = Decimal("100"),
    index: InvoiceBlockIndex | None = None,
) -> list[CanonicalTransaction]:
    """Return a deterministic candidate set using indexed coarse blocking.

    Blocking is intentionally permissive: it can admit false candidates, but
    should not exclude records that satisfy the configured matching window.
    When no index is supplied, the original scan-based behavior is retained
    for callers that use this helper directly.
    """
    used = used or set()
    bank_name = normalize_name(bank.counterparty_name)
    bank_tokens = name_tokens(bank.counterparty_name)
    target_bucket = amount_bucket(bank.amount, amount_bucket_size)

    if index is None:
        source = invoices
    else:
        candidate_ids: set[str] = set()
        for bucket in (target_bucket - 1, target_bucket, target_bucket + 1):
            candidate_ids.update(index.by_amount_bucket.get(bucket, ()))
        if bank_name:
            candidate_ids.update(index.by_normalized_name.get(bank_name, ()))
        for token in bank_tokens:
            candidate_ids.update(index.by_token.get(token, ()))
        source = [
            index.invoices_by_id[record_id]
            for record_id in sorted(candidate_ids)
            if record_id in index.invoices_by_id
        ]

    result: list[CanonicalTransaction] = []
    for invoice in source:
        if invoice.source_record_id in used:
            continue
        if abs(invoice.transaction_date - bank.transaction_date).days > date_tolerance_days:
            continue
        if abs(invoice.amount - bank.amount) > amount_tolerance:
            invoice_tokens = name_tokens(invoice.counterparty_name)
            if not (bank_tokens and bank_tokens.intersection(invoice_tokens)):
                continue
        inv_bucket = amount_bucket(invoice.amount, amount_bucket_size)
        inv_name = normalize_name(invoice.counterparty_name)
        if inv_bucket in {target_bucket - 1, target_bucket, target_bucket + 1} or (
            bank_name and inv_name == bank_name
        ) or (bank_tokens and bank_tokens.intersection(name_tokens(invoice.counterparty_name))):
            result.append(invoice)
    return result
