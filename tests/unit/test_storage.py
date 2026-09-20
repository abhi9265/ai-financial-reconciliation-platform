from datetime import datetime, timezone
from decimal import Decimal

from reconciliation_platform.decisioning.review import build_review_cases
from reconciliation_platform.models.canonical_transaction import SourceSystem, TransactionType
from reconciliation_platform.storage.sqlite import SQLiteStore
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


def _tx() -> CanonicalTransaction:
    return CanonicalTransaction.from_business_fields(
        transaction_id="B1",
        source_system=SourceSystem.BANK,
        source_record_id="B1",
        transaction_date="2026-01-01",
        transaction_type=TransactionType.PAYMENT,
        amount=Decimal("100.00"),
        currency="INR",
        amount_direction="DEBIT",
        debit=Decimal("100.00"),
        description="vendor payment",
        ingestion_batch_id="BATCH1",
        ingested_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_store_is_idempotent_for_batches_records_and_reviews():
    store = SQLiteStore(":memory:")
    created_at = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()

    assert store.register_batch(
        batch_id="BATCH1",
        source_system="BANK",
        file_fingerprint="fp1",
        schema_version="1.0",
        created_at=created_at,
    )
    assert not store.register_batch(
        batch_id="BATCH1",
        source_system="BANK",
        file_fingerprint="fp1",
        schema_version="1.0",
        created_at=created_at,
    )

    tx = _tx()
    assert store.register_transactions([tx], batch_id="BATCH1", created_at=created_at) == (1, 0)
    assert store.register_transactions([tx], batch_id="BATCH1", created_at=created_at) == (0, 1)

    decision = __import__(
        "reconciliation_platform.reconciliation.engine",
        fromlist=["ReconciliationDecision"],
    ).ReconciliationDecision(
        "B1", "I1", "REVIEW", "FUZZY", 0.7, "ambiguous", ()
    )
    cases = build_review_cases([decision], created_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert store.save_review_cases(cases) == 1
    assert store.save_review_cases(cases) == 0
    assert store.review_case_count() == 1
