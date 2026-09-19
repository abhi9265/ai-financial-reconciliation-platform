from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, compute_record_hash


def test_hash_is_sha256_hex():
    transaction = CanonicalTransaction.from_business_fields(
        transaction_id="txn-1",
        source_system="bank",
        source_record_id="row-1",
        transaction_date="2026-01-15",
        transaction_type="PAYMENT",
        amount="100.00",
        currency="INR",
        ingestion_batch_id="batch-1",
        ingested_at="2026-01-15T10:00:00+05:30",
    )

    digest = compute_record_hash(transaction)

    assert len(digest) == 64
    assert digest == transaction.record_hash
    assert all(character in "0123456789abcdef" for character in digest)


def test_decimal_formatting_does_not_change_business_hash():
    first = CanonicalTransaction.from_business_fields(
        transaction_id="txn-1", source_system="bank", source_record_id="row-1",
        transaction_date="2026-01-15", transaction_type="PAYMENT", amount="100.00",
        currency="INR", ingestion_batch_id="batch-1", ingested_at="2026-01-15T10:00:00+05:30",
    )
    second = CanonicalTransaction.from_business_fields(
        transaction_id="txn-2", source_system="invoice", source_record_id="invoice-99",
        transaction_date="2026-01-15", transaction_type="PAYMENT", amount="100",
        currency="INR", ingestion_batch_id="batch-99", ingested_at="2026-02-01T10:00:00+05:30",
    )

    assert first.record_hash == second.record_hash
