import pytest

from reconciliation_platform.ingestion.contracts import (
    IngestionContractError,
    normalize_columns,
    validate_columns,
    validate_rows,
)
from reconciliation_platform.models.canonical_transaction import SourceSystem


def test_bank_contract_accepts_required_and_optional_columns():
    columns = validate_columns(
        SourceSystem.BANK,
        ["Transaction Date", "Amount", "Description", "Source Record ID", "Debit"],
    )

    assert columns == (
        "transaction_date",
        "amount",
        "description",
        "source_record_id",
        "debit",
    )


def test_missing_required_column_is_rejected():
    with pytest.raises(IngestionContractError, match="missing required columns"):
        validate_columns(
            SourceSystem.PURCHASE_REGISTER,
            ["invoice_number", "invoice_date", "amount", "source_record_id"],
        )


def test_unsupported_column_is_rejected():
    with pytest.raises(IngestionContractError, match="unsupported columns"):
        validate_columns(
            SourceSystem.BANK,
            ["transaction_date", "amount", "description", "source_record_id", "customer_email"],
        )


def test_header_normalization_collision_is_rejected():
    with pytest.raises(IngestionContractError, match="duplicate columns"):
        normalize_columns(["Invoice Number", "invoice-number"])


def test_blank_header_is_rejected():
    with pytest.raises(IngestionContractError, match="column name"):
        normalize_columns(["Invoice Number", "   "])


def test_rows_must_match_normalized_contract():
    columns = ["Invoice Number", "Invoice Date", "Amount", "Counterparty Name", "Source Record ID"]
    rows = [
        {
            "invoice_number": "INV-1",
            "invoice_date": "2026-01-15",
            "amount": "100.00",
            "counterparty_name": "ABC",
            "source_record_id": "row-1",
        }
    ]

    assert validate_rows(rows, columns) == 1


def test_row_with_unknown_field_is_rejected():
    columns = ["invoice_number", "invoice_date", "amount", "counterparty_name", "source_record_id"]
    rows = [{
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-15",
        "amount": "100.00",
        "counterparty_name": "ABC",
        "source_record_id": "row-1",
        "unexpected": "value",
    }]

    with pytest.raises(IngestionContractError, match="row 1 contains unsupported"):
        validate_rows(rows, columns)


def test_row_with_missing_field_is_rejected():
    columns = ["invoice_number", "invoice_date", "amount", "counterparty_name", "source_record_id"]
    rows = [{
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-15",
        "amount": "100.00",
        "counterparty_name": "ABC",
    }]

    with pytest.raises(IngestionContractError, match="row 1 is missing"):
        validate_rows(rows, columns)
