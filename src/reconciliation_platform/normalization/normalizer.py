"""Source-to-canonical normalization for synthetic financial records."""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Mapping
from reconciliation_platform.models.canonical_transaction import (
    AmountDirection, CanonicalTransaction, CounterpartyType, SourceSystem, TransactionType,
)
from reconciliation_platform.normalization.context import NormalizationContext

class NormalizationError(ValueError):
    """Raised when a source row cannot be converted into the canonical contract."""

def _decimal(value: object, field: str, *, allow_none: bool = True) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if allow_none:
            return None
        raise NormalizationError(f"{field} is required")
    try:
        return Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise NormalizationError(f"{field} is not a valid decimal: {value!r}") from exc

def _date(value: object, field: str) -> date:
    if value is None or str(value).strip() == "":
        raise NormalizationError(f"{field} is required")
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        raise NormalizationError(f"{field} is not ISO date: {value!r}") from exc

def _text(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None

def normalize_row(row: Mapping[str, object], *, context: NormalizationContext, row_number: int) -> CanonicalTransaction:
    source = context.source_system
    if source is SourceSystem.BANK:
        return _normalize_bank(row, context=context, row_number=row_number)
    if source is SourceSystem.PURCHASE_REGISTER:
        return _normalize_purchase(row, context=context, row_number=row_number)
    raise NormalizationError(f"no normalizer registered for source: {source.value}")

def normalize_rows(rows: list[Mapping[str, object]], *, context: NormalizationContext) -> list[CanonicalTransaction]:
    return [normalize_row(row, context=context, row_number=i) for i, row in enumerate(rows, start=2)]

def _common(data: dict, context: NormalizationContext, row_number: int) -> dict:
    data.update({
        "source_system": context.source_system,
        "currency": context.currency,
        "source_file_name": context.source_file_name,
        "source_file_hash": context.source_file_hash,
        "source_row_number": row_number,
        "source_schema_version": context.source_schema_version,
        "ingestion_batch_id": context.ingestion_batch_id,
        "ingested_at": context.ingested_at,
    })
    return data

def _normalize_bank(row: Mapping[str, object], *, context: NormalizationContext, row_number: int) -> CanonicalTransaction:
    amount = _decimal(row.get("amount"), "amount", allow_none=False)
    debit = _decimal(row.get("debit"), "debit")
    credit = _decimal(row.get("credit"), "credit")
    if amount is None or amount <= 0:
        raise NormalizationError("amount must be positive")
    if credit is not None and credit > 0:
        direction = AmountDirection.CREDIT
        # Some bank exports carry a pre-adjustment debit alongside the effective credit.
        # Canonical semantics preserve the effective side; raw Bronze retains the source row.
        canonical_debit, canonical_credit = None, amount
        tx_type = TransactionType.RECEIPT
    elif debit is not None and debit > 0:
        direction = AmountDirection.DEBIT
        canonical_debit, canonical_credit = amount, None
        tx_type = TransactionType.PAYMENT
    else:
        raise NormalizationError("bank row must contain a positive debit or credit")
    return CanonicalTransaction.from_business_fields(**_common({
        "transaction_id": str(row["transaction_id"]).strip(),
        "source_record_id": str(row["transaction_id"]).strip(),
        "transaction_date": _date(row.get("transaction_date"), "transaction_date"),
        "value_date": _date(row.get("value_date"), "value_date") if row.get("value_date") else None,
        "transaction_type": tx_type,
        "amount": amount,
        "amount_direction": direction,
        "debit": canonical_debit,
        "credit": canonical_credit,
        "description": _text(row.get("narration")),
        "reference_number": _text(row.get("reference")),
        "counterparty_name": _text(row.get("narration")),
        "counterparty_type": CounterpartyType.VENDOR,
        "bank_account": _text(row.get("account_number")),
    }, context, row_number))

def _normalize_purchase(row: Mapping[str, object], *, context: NormalizationContext, row_number: int) -> CanonicalTransaction:
    total = _decimal(row.get("total"), "total", allow_none=False)
    cgst = _decimal(row.get("cgst"), "cgst") or Decimal("0")
    sgst = _decimal(row.get("sgst"), "sgst") or Decimal("0")
    igst = _decimal(row.get("igst"), "igst") or Decimal("0")
    return CanonicalTransaction.from_business_fields(**_common({
        "transaction_id": str(row["invoice_record_id"]).strip(),
        "source_record_id": str(row["invoice_record_id"]).strip(),
        "transaction_date": _date(row.get("invoice_date"), "invoice_date"),
        "invoice_date": _date(row.get("invoice_date"), "invoice_date"),
        "transaction_type": TransactionType.PURCHASE,
        "amount": total,
        "description": f"Purchase invoice {str(row['invoice_number']).strip()}",
        "invoice_number": str(row["invoice_number"]).strip(),
        "counterparty_name": _text(row.get("vendor_name")),
        "counterparty_type": CounterpartyType.VENDOR,
        "counterparty_gstin": _text(row.get("gstin")),
        "taxable_amount": _decimal(row.get("taxable_value"), "taxable_value", allow_none=False),
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_tax": cgst + sgst + igst,
    }, context, row_number))
