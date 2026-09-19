"""Executable canonical transaction contract.

The JSON Schema documents the interchange contract. This module adds Python-level
validation and deterministic record hashing for application code and tests.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator


class SourceSystem(str, Enum):
    BANK = "bank"
    PURCHASE_REGISTER = "purchase_register"
    SALES_REGISTER = "sales_register"
    TALLY = "tally"
    INVOICE = "invoice"
    GST = "gst"


class TransactionType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    PAYMENT = "PAYMENT"
    RECEIPT = "RECEIPT"
    REFUND = "REFUND"
    FEE = "FEE"
    TAX = "TAX"
    JOURNAL = "JOURNAL"
    OTHER = "OTHER"


class AmountDirection(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"


class CounterpartyType(str, Enum):
    VENDOR = "VENDOR"
    CUSTOMER = "CUSTOMER"
    BANK = "BANK"
    TAX_AUTHORITY = "TAX_AUTHORITY"
    EMPLOYEE = "EMPLOYEE"
    OTHER = "OTHER"


# Stable business facts used to identify a normalized transaction. Volatile
# ingestion metadata and source lineage are deliberately excluded so retries
# produce the same hash and identical business events can be compared across sources.
HASH_FIELDS = (
    "transaction_date",
    "value_date",
    "invoice_date",
    "transaction_type",
    "amount",
    "currency",
    "amount_direction",
    "debit",
    "credit",
    "description",
    "reference_number",
    "invoice_number",
    "counterparty_name",
    "counterparty_type",
    "counterparty_gstin",
    "taxable_amount",
    "cgst",
    "sgst",
    "igst",
    "total_tax",
    "account_name",
    "bank_account",
)


def _hash_value(value: Any) -> Any:
    """Convert supported values into deterministic JSON-safe primitives."""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _hash_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_hash_value(item) for item in value]
    return value


def compute_record_hash(transaction: "CanonicalTransaction") -> str:
    """Return the SHA-256 hash of the stable canonical business payload."""
    payload = {
        field: _hash_value(getattr(transaction, field)) for field in HASH_FIELDS
    }
    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class CanonicalTransaction(BaseModel):
    """Normalized financial transaction consumed by downstream reconciliation."""

    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1)
    source_system: SourceSystem
    source_record_id: str = Field(min_length=1)

    transaction_date: date
    value_date: date | None = None
    invoice_date: date | None = None
    transaction_type: TransactionType

    amount: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    amount_direction: AmountDirection | None = None
    debit: Decimal | None = Field(default=None, ge=0)
    credit: Decimal | None = Field(default=None, ge=0)

    description: str | None = None
    reference_number: str | None = None
    invoice_number: str | None = None

    counterparty_name: str | None = None
    counterparty_type: CounterpartyType | None = None
    counterparty_gstin: str | None = Field(default=None, pattern=r"^[0-9A-Z]{15}$")

    taxable_amount: Decimal | None = Field(default=None, ge=0)
    cgst: Decimal | None = Field(default=None, ge=0)
    sgst: Decimal | None = Field(default=None, ge=0)
    igst: Decimal | None = Field(default=None, ge=0)
    total_tax: Decimal | None = Field(default=None, ge=0)

    account_name: str | None = None
    bank_account: str | None = None

    source_file_name: str | None = None
    source_file_hash: str | None = None
    source_row_number: int | None = Field(default=None, ge=1)
    source_schema_version: str | None = None

    ingestion_batch_id: str = Field(min_length=1)
    ingested_at: datetime
    record_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_amount_direction(self) -> "CanonicalTransaction":
        if self.amount_direction is None:
            if self.debit is not None or self.credit is not None:
                raise ValueError("debit/credit must be null when amount_direction is null")
            return self

        if self.amount_direction == AmountDirection.DEBIT:
            if self.debit != self.amount or self.credit is not None:
                raise ValueError("DEBIT requires debit=amount and credit=null")
        elif self.amount_direction == AmountDirection.CREDIT:
            if self.credit != self.amount or self.debit is not None:
                raise ValueError("CREDIT requires credit=amount and debit=null")
        return self

    @model_validator(mode="after")
    def validate_tax_total(self) -> "CanonicalTransaction":
        components = (self.cgst, self.sgst, self.igst)
        if self.total_tax is not None and all(component is not None for component in components):
            component_total = sum(components, Decimal("0"))
            if self.total_tax != component_total:
                raise ValueError("total_tax must equal cgst + sgst + igst")
        return self

    @model_validator(mode="after")
    def validate_record_hash(self, info: ValidationInfo) -> "CanonicalTransaction":
        if not (info.context or {}).get("skip_record_hash"):
            expected = compute_record_hash(self)
            if self.record_hash != expected:
                raise ValueError("record_hash does not match the canonical business payload")
        return self

    @classmethod
    def from_business_fields(cls, **data: Any) -> "CanonicalTransaction":
        """Build a transaction while computing its deterministic record hash."""
        data = dict(data)
        data["record_hash"] = "0" * 64
        validated = cls.model_validate(data, context={"skip_record_hash": True})
        return validated.model_copy(update={"record_hash": compute_record_hash(validated)})
