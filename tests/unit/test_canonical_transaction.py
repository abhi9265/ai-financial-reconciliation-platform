from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


def valid_data(**overrides):
    data = {
        "transaction_id": "txn_000001",
        "source_system": "bank",
        "source_record_id": "bank-row-1",
        "transaction_date": "2026-01-15",
        "transaction_type": "PAYMENT",
        "amount": "118000.00",
        "currency": "INR",
        "amount_direction": "DEBIT",
        "debit": "118000.00",
        "credit": None,
        "counterparty_name": "ABC INDUSTRIES PVT LTD",
        "counterparty_type": "VENDOR",
        "counterparty_gstin": "24ABCDE1234F1Z5",
        "invoice_number": "INV-1042",
        "invoice_date": "2026-01-14",
        "taxable_amount": "100000.00",
        "cgst": "9000.00",
        "sgst": "9000.00",
        "igst": "0.00",
        "total_tax": "18000.00",
        "ingestion_batch_id": "bank-2026-01-15-001",
        "ingested_at": "2026-01-15T18:30:00+05:30",
    }
    data.update(overrides)
    return data


def make_transaction(**overrides):
    return CanonicalTransaction.from_business_fields(**valid_data(**overrides))


def test_valid_transaction_is_accepted_and_hash_is_computed():
    transaction = make_transaction()

    assert transaction.amount == Decimal("118000.00")
    assert transaction.transaction_type == "PAYMENT"
    assert len(transaction.record_hash) == 64


def test_hash_is_stable_across_batch_and_ingestion_timestamp_changes():
    first = make_transaction(ingestion_batch_id="batch-a", ingested_at="2026-01-15T18:30:00+05:30")
    second = make_transaction(ingestion_batch_id="batch-b", ingested_at="2026-01-16T09:00:00+05:30")

    assert first.record_hash == second.record_hash


def test_hash_changes_when_business_amount_changes():
    first = make_transaction(amount="118000.00", debit="118000.00")
    second = make_transaction(amount="119000.00", debit="119000.00")

    assert first.record_hash != second.record_hash


def test_hash_changes_when_counterparty_changes():
    first = make_transaction(counterparty_name="ABC INDUSTRIES PVT LTD")
    second = make_transaction(counterparty_name="XYZ INDUSTRIES PVT LTD")

    assert first.record_hash != second.record_hash


def test_debit_requires_debit_amount_and_null_credit():
    with pytest.raises(ValidationError, match="DEBIT requires debit=amount"):
        make_transaction(debit="117000.00")

    with pytest.raises(ValidationError, match="DEBIT requires debit=amount"):
        make_transaction(credit="118000.00")


def test_credit_requires_credit_amount_and_null_debit():
    transaction = make_transaction(
        amount_direction="CREDIT",
        debit=None,
        credit="118000.00",
        transaction_type="RECEIPT",
    )

    assert transaction.credit == Decimal("118000.00")
    assert transaction.debit is None


def test_directionless_transaction_cannot_have_debit_or_credit():
    with pytest.raises(ValidationError, match="debit/credit must be null"):
        make_transaction(amount_direction=None, debit="118000.00", credit=None)


def test_amount_must_be_positive():
    with pytest.raises(ValidationError):
        make_transaction(amount="0", debit="0")


def test_currency_must_be_three_uppercase_letters():
    with pytest.raises(ValidationError):
        make_transaction(currency="IN")

    with pytest.raises(ValidationError):
        make_transaction(currency="inr")


def test_invalid_gstin_is_rejected():
    with pytest.raises(ValidationError):
        make_transaction(counterparty_gstin="24ABCDE1234F1Z")


def test_tax_total_must_equal_components_when_all_components_are_present():
    with pytest.raises(ValidationError, match="total_tax must equal"):
        make_transaction(total_tax="17000.00")


def test_partial_tax_components_do_not_force_a_total():
    transaction = make_transaction(igst=None, total_tax=None)
    assert transaction.cgst == Decimal("9000.00")


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        make_transaction(unexpected_field="not allowed")


def test_record_hash_must_match_business_payload():
    transaction = make_transaction()
    payload = transaction.model_dump()
    payload["record_hash"] = "0" * 64

    with pytest.raises(ValidationError, match="record_hash does not match"):
        CanonicalTransaction.model_validate(payload)


def test_hash_excludes_volatile_and_lineage_fields():
    first = make_transaction(
        transaction_id="txn-1", source_record_id="source-row-1", source_file_name="file-a.csv",
        source_row_number=1, ingestion_batch_id="batch-a",
        ingested_at=datetime.fromisoformat("2026-01-15T18:30:00+05:30"),
    )
    second = make_transaction(
        transaction_id="txn-2", source_record_id="source-row-99", source_file_name="file-b.csv",
        source_row_number=99, ingestion_batch_id="batch-b",
        ingested_at=datetime.fromisoformat("2026-02-01T10:00:00+05:30"),
    )

    assert first.record_hash == second.record_hash
