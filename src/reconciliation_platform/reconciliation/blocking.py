"""Candidate blocking for scalable reconciliation.

Blocking reduces the expensive matching surface before fuzzy scoring. It is an
optimization and a safety boundary: a record that cannot satisfy the coarse
candidate contract is never considered by the more expensive matcher.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
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


def build_invoice_blocks(
    invoices: Iterable[CanonicalTransaction],
    *,
    amount_bucket_size: Decimal = Decimal("100"),
) -> dict[tuple[int, str], list[CanonicalTransaction]]:
    blocks: dict[tuple[int, str], list[CanonicalTransaction]] = defaultdict(list)
    for invoice in invoices:
        blocks[(amount_bucket(invoice.amount, amount_bucket_size), normalize_name(invoice.counterparty_name))].append(invoice)
    return dict(blocks)


def candidate_invoices(
    bank: CanonicalTransaction,
    invoices: list[CanonicalTransaction],
    *,
    used: set[str] | None = None,
    date_tolerance_days: int = 7,
    amount_tolerance: Decimal = Decimal("25"),
    amount_bucket_size: Decimal = Decimal("100"),
) -> list[CanonicalTransaction]:
    """Return a small deterministic candidate set using coarse blocking.

    Blocking is intentionally permissive: it can admit false candidates, but
    should not exclude records that satisfy the configured matching window.
    """
    used = used or set()
    bank_name = normalize_name(bank.counterparty_name)
    bank_tokens = name_tokens(bank.counterparty_name)
    target_bucket = amount_bucket(bank.amount, amount_bucket_size)
    result: list[CanonicalTransaction] = []

    for invoice in invoices:
        if invoice.source_record_id in used:
            continue
        if abs(invoice.transaction_date - bank.transaction_date).days > date_tolerance_days:
            continue
        if abs(invoice.amount - bank.amount) > amount_tolerance:
            # Keep same-name candidates because one-to-many/partial payment
            # matching can legitimately have a material amount difference.
            invoice_tokens = name_tokens(invoice.counterparty_name)
            if not (bank_tokens and bank_tokens.intersection(invoice_tokens)):
                continue
        inv_bucket = amount_bucket(invoice.amount, amount_bucket_size)
        inv_name = normalize_name(invoice.counterparty_name)
        if inv_bucket in {target_bucket - 1, target_bucket, target_bucket + 1} or (
            bank_name and inv_name == bank_name
        ):
            result.append(invoice)
    return result
