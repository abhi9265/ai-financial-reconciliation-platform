"""Candidate blocking for scalable reconciliation."""
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
    by_name: dict[str, tuple[str, ...]]
    by_token: dict[str, tuple[str, ...]]
    by_amount_bucket: dict[int, tuple[str, ...]]
    invoices: dict[str, CanonicalTransaction]


def build_invoice_index(
    invoices: Iterable[CanonicalTransaction],
    *,
    amount_bucket_size: Decimal = Decimal("100"),
) -> InvoiceBlockIndex:
    by_name: dict[str, list[str]] = defaultdict(list)
    by_token: dict[str, list[str]] = defaultdict(list)
    by_amount_bucket: dict[int, list[str]] = defaultdict(list)
    invoice_map: dict[str, CanonicalTransaction] = {}

    for invoice in invoices:
        rid = invoice.source_record_id
        invoice_map[rid] = invoice
        by_name[normalize_name(invoice.counterparty_name)].append(rid)
        for token in name_tokens(invoice.counterparty_name):
            by_token[token].append(rid)
        by_amount_bucket[amount_bucket(invoice.amount, amount_bucket_size)].append(rid)

    return InvoiceBlockIndex(
        by_name={k: tuple(v) for k, v in by_name.items()},
        by_token={k: tuple(v) for k, v in by_token.items()},
        by_amount_bucket={k: tuple(v) for k, v in by_amount_bucket.items()},
        invoices=invoice_map,
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
    """Return a permissive candidate set without scanning every invoice."""
    used = used or set()
    idx = index or build_invoice_index(invoices, amount_bucket_size=amount_bucket_size)

    ids: set[str] = set()
    bank_name = normalize_name(bank.counterparty_name)
    bank_tokens = name_tokens(bank.counterparty_name)
    target_bucket = amount_bucket(bank.amount, amount_bucket_size)

    if bank_name:
        ids.update(idx.by_name.get(bank_name, ()))
    for token in bank_tokens:
        ids.update(idx.by_token.get(token, ()))
    for bucket in (target_bucket - 1, target_bucket, target_bucket + 1):
        ids.update(idx.by_amount_bucket.get(bucket, ()))

    result: list[CanonicalTransaction] = []
    for rid in sorted(ids):
        if rid in used:
            continue
        invoice = idx.invoices[rid]
        if abs(invoice.transaction_date - bank.transaction_date).days > date_tolerance_days:
            continue
        if abs(invoice.amount - bank.amount) > amount_tolerance:
            if not (bank_tokens and bank_tokens.intersection(name_tokens(invoice.counterparty_name))):
                continue
        result.append(invoice)
    return result


def build_invoice_blocks(
    invoices: Iterable[CanonicalTransaction],
    *,
    amount_bucket_size: Decimal = Decimal("100"),
) -> dict[tuple[int, str], list[CanonicalTransaction]]:
    blocks: dict[tuple[int, str], list[CanonicalTransaction]] = defaultdict(list)
    for invoice in invoices:
        blocks[(amount_bucket(invoice.amount, amount_bucket_size), normalize_name(invoice.counterparty_name))].append(invoice)
    return dict(blocks)
