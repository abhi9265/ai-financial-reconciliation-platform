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
        ["Transaction ID", "Transaction Date", "Amount", "Narration", "Reference", "Account Number", "Debit"],
    )

    assert columns == (
        "transaction_id",
        "transaction_date",
        "amount",
        "narration",
        "reference",
        "account_number",
        "debit",
    )


def test_missing_required_column_is_rejected():
    with pytest.raises(IngestionContractError, match="missing required columns"):
        validate_columns(
            SourceSystem.PURCHASE_REGISTER,
            ["invoice_record_id", "invoice_number", "invoice_date", "vendor_name", "gstin", "taxable_value"],
        )


def test_unsupported_column_is_rejected():
    with pytest.raises(IngestionContractError, match="unsupported columns"):
        validate_columns(
            SourceSystem.BANK,
            ["transaction_id", "transaction_date", "amount", "narration", "reference", "account_number", "customer_email"],
        )


def test_header_normalization_collision_is_rejected():
    with pytest.raises(IngestionContractError, match="duplicate columns"):
        normalize_columns(["Invoice Number", "invoice-number"])


def test_blank_header_is_rejected():
    with pytest.raises(IngestionContractError, match="column name"):
        normalize_columns(["Invoice Number", "   "])


def test_rows_must_match_normalized_contract():
    columns = [
        "Invoice Record ID", "Invoice Number", "Invoice Date", "Vendor Name",
        "GSTIN", "Taxable Value", "Total",
    ]
    rows = [{
        "invoice_record_id": "INVREC-1",
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-15",
        "vendor_name": "ABC",
        "gstin": "24ABCDE1234F1Z5",
        "taxable_value": "100.00",
        "total": "118.00",
    }]

    assert validate_rows(rows, columns) == 1


def test_row_with_unknown_field_is_rejected():
    columns = [
        "invoice_record_id", "invoice_number", "invoice_date", "vendor_name",
        "gstin", "taxable_value", "total",
    ]
    rows = [{
        "invoice_record_id": "INVREC-1",
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-15",
        "vendor_name": "ABC",
        "gstin": "24ABCDE1234F1Z5",
        "taxable_value": "100.00",
        "total": "118.00",
        "unexpected": "value",
    }]

    with pytest.raises(IngestionContractError, match="row 1 contains unsupported"):
        validate_rows(rows, columns)


def test_row_with_missing_field_is_rejected():
    columns = [
        "invoice_record_id", "invoice_number", "invoice_date", "vendor_name",
        "gstin", "taxable_value", "total",
    ]
    rows = [{
        "invoice_record_id": "INVREC-1",
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-15",
        "vendor_name": "ABC",
        "gstin": "24ABCDE1234F1Z5",
        "taxable_value": "100.00",
    }]

    with pytest.raises(IngestionContractError, match="row 1 is missing"):
        validate_rows(rows, columns)
