"""Source-specific ingestion contracts for Phase 1.

Contracts validate tabular source shape before normalization. They intentionally
operate on column names and rows only; parsing and reconciliation remain separate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from reconciliation_platform.models.canonical_transaction import SourceSystem


class IngestionContractError(ValueError):
    """Raised when a source payload violates its ingestion contract."""


@dataclass(frozen=True)
class SourceContract:
    """Minimum source contract required before records enter normalization."""

    source_system: SourceSystem
    required_columns: frozenset[str]
    optional_columns: frozenset[str] = frozenset()


SOURCE_CONTRACTS: Mapping[SourceSystem, SourceContract] = {
    SourceSystem.BANK: SourceContract(
        SourceSystem.BANK,
        frozenset({"transaction_id", "transaction_date", "amount", "narration", "reference", "account_number"}),
        frozenset({"value_date", "debit", "credit"}),
    ),
    SourceSystem.PURCHASE_REGISTER: SourceContract(
        SourceSystem.PURCHASE_REGISTER,
        frozenset({"invoice_record_id", "invoice_number", "invoice_date", "vendor_name", "gstin", "taxable_value", "total"}),
        frozenset({"cgst", "sgst", "igst"}),
    ),
    SourceSystem.SALES_REGISTER: SourceContract(
        SourceSystem.SALES_REGISTER,
        frozenset({"invoice_number", "invoice_date", "amount", "counterparty_name", "source_record_id"}),
        frozenset({"counterparty_gstin", "taxable_amount", "cgst", "sgst", "igst", "total_tax"}),
    ),
    SourceSystem.TALLY: SourceContract(
        SourceSystem.TALLY,
        frozenset({"transaction_date", "amount", "transaction_type", "source_record_id"}),
        frozenset({"reference_number", "account_name", "description", "debit", "credit"}),
    ),
    SourceSystem.INVOICE: SourceContract(
        SourceSystem.INVOICE,
        frozenset({"invoice_number", "invoice_date", "amount", "source_record_id"}),
        frozenset({"counterparty_name", "counterparty_gstin", "taxable_amount", "cgst", "sgst", "igst", "total_tax"}),
    ),
    SourceSystem.GST: SourceContract(
        SourceSystem.GST,
        frozenset({"invoice_number", "invoice_date", "amount", "counterparty_gstin", "source_record_id"}),
        frozenset({"taxable_amount", "cgst", "sgst", "igst", "total_tax"}),
    ),
}


def normalize_column_name(value: str) -> str:
    """Normalize source headers into stable snake_case names."""
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    if not normalized:
        raise IngestionContractError("column name cannot be empty")
    return normalized


def normalize_columns(columns: Iterable[str]) -> tuple[str, ...]:
    """Normalize headers and reject collisions created by normalization."""
    normalized = tuple(normalize_column_name(column) for column in columns)
    duplicates = sorted({column for column in normalized if normalized.count(column) > 1})
    if duplicates:
        raise IngestionContractError(
            f"duplicate columns after normalization: {', '.join(duplicates)}"
        )
    return normalized


def validate_columns(source_system: SourceSystem, columns: Iterable[str]) -> tuple[str, ...]:
    """Validate required/allowed columns and return normalized headers."""
    normalized = normalize_columns(columns)
    contract = SOURCE_CONTRACTS[source_system]
    actual = set(normalized)

    missing = sorted(contract.required_columns - actual)
    if missing:
        raise IngestionContractError(
            f"{source_system.value} source is missing required columns: {', '.join(missing)}"
        )

    allowed = contract.required_columns | contract.optional_columns
    unexpected = sorted(actual - allowed)
    if unexpected:
        raise IngestionContractError(
            f"{source_system.value} source contains unsupported columns: {', '.join(unexpected)}"
        )

    return normalized


def validate_rows(rows: Iterable[Mapping[str, object]], columns: Iterable[str]) -> int:
    """Validate that rows contain no unknown keys and have a stable shape."""
    normalized_columns = set(normalize_columns(columns))
    count = 0
    for index, row in enumerate(rows, start=1):
        normalized_keys = {normalize_column_name(str(key)) for key in row}
        unexpected = sorted(normalized_keys - normalized_columns)
        if unexpected:
            raise IngestionContractError(
                f"row {index} contains unsupported columns: {', '.join(unexpected)}"
            )
        missing = sorted(normalized_columns - normalized_keys)
        if missing:
            raise IngestionContractError(
                f"row {index} is missing columns: {', '.join(missing)}"
            )
        count += 1
    return count
