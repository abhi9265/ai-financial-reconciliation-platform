"""Deterministic adversarial benchmark generator.

The generator creates labeled cases rather than relying on hand-picked rows.
This makes benchmark results reproducible and lets the benchmark evolve as
the matching engine becomes more capable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from random import Random

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, SourceSystem, TransactionType


@dataclass(frozen=True)
class AdversarialCase:
    bank: CanonicalTransaction
    invoices: tuple[CanonicalTransaction, ...]
    relationship: str
    expected_invoice_ids: tuple[str, ...]


def _tx(
    source_system: SourceSystem,
    record_id: str,
    amount: Decimal,
    day: int,
    name: str,
    *,
    ref: str | None = None,
    invoice_number: str | None = None,
    transaction_type: TransactionType,
) -> CanonicalTransaction:
    return CanonicalTransaction.from_business_fields(
        transaction_id=record_id,
        source_system=source_system,
        source_record_id=record_id,
        transaction_date=f"2026-08-{day:02d}",
        invoice_date=f"2026-08-{day:02d}" if invoice_number else None,
        transaction_type=transaction_type,
        amount=amount,
        currency="INR",
        description=name,
        reference_number=ref,
        invoice_number=invoice_number,
        counterparty_name=name,
        ingestion_batch_id="adversarial",
        ingested_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


def generate_adversarial_cases(seed: int = 42, cases: int = 250, one_to_many_rate: float = 0.12, partial_rate: float = 0.12) -> list[AdversarialCase]:
    rng = Random(seed)
    result: list[AdversarialCase] = []
    for n in range(cases):
        day = 1 + (n % 20)
        canonical_name = f"Vendor {n:04d}"
        variant = canonical_name.replace("Vendor", "VEND.").replace(" ", "  ")
        invoice_id = f"I{n:06d}"
        bank_id = f"B{n:06d}"
        amount = Decimal(rng.randrange(500, 250000)).quantize(Decimal("0.01"))
        if rng.random() < one_to_many_rate:
            a = (amount * Decimal("0.40")).quantize(Decimal("0.01"))
            b = (amount - a).quantize(Decimal("0.01"))
            invoices = (
                _tx(SourceSystem.PURCHASE_REGISTER, invoice_id + "A", a, day, variant, ref=None, invoice_number=invoice_id + "A", transaction_type=TransactionType.PURCHASE),
                _tx(SourceSystem.PURCHASE_REGISTER, invoice_id + "B", b, day, variant, ref=None, invoice_number=invoice_id + "B", transaction_type=TransactionType.PURCHASE),
            )
            bank = _tx(SourceSystem.BANK, bank_id, amount, day + 1 if day < 20 else day, canonical_name, ref=None, transaction_type=TransactionType.PAYMENT)
            result.append(AdversarialCase(bank, invoices, "MATCH", tuple(x.source_record_id for x in invoices)))
        elif rng.random() < partial_rate:
            invoice = _tx(SourceSystem.PURCHASE_REGISTER, invoice_id, amount, day, variant, ref=invoice_id, invoice_number=invoice_id, transaction_type=TransactionType.PURCHASE)
            payment = (amount * Decimal("0.40")).quantize(Decimal("0.01"))
            bank = _tx(SourceSystem.BANK, bank_id, payment, day + 1 if day < 20 else day, canonical_name, ref=invoice_id, transaction_type=TransactionType.PAYMENT)
            result.append(AdversarialCase(bank, (invoice,), "PARTIAL", (invoice_id,)))
        else:
            invoice = _tx(SourceSystem.PURCHASE_REGISTER, invoice_id, amount, day, variant, ref=invoice_id, invoice_number=invoice_id, transaction_type=TransactionType.PURCHASE)
            if n % 17 == 0:
                bank = _tx(SourceSystem.BANK, bank_id, amount + Decimal("7.50"), day, canonical_name, ref=invoice_id, transaction_type=TransactionType.PAYMENT)
                result.append(AdversarialCase(bank, (invoice,), "REVIEW", (invoice_id,)))
            else:
                bank = _tx(SourceSystem.BANK, bank_id, amount, day + 1 if day < 20 else day, canonical_name, ref=invoice_id, transaction_type=TransactionType.PAYMENT)
                result.append(AdversarialCase(bank, (invoice,), "MATCH", (invoice_id,)))
    return result
