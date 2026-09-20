from datetime import datetime, timezone
from decimal import Decimal

from reconciliation_platform.models.canonical_transaction import (
    CanonicalTransaction,
    SourceSystem,
    TransactionType,
)
from reconciliation_platform.reconciliation.engine import ReconciliationConfig, reconcile


def tx(i, amount, ref, day=1, name="Vendor"):
    return CanonicalTransaction.from_business_fields(
        transaction_id=i, source_system=SourceSystem.BANK, source_record_id=i,
        transaction_date=f"2026-07-{day:02d}", transaction_type=TransactionType.PAYMENT,
        amount=Decimal(str(amount)), currency="INR", description=name,
        reference_number=ref, counterparty_name=name, ingestion_batch_id="b",
        ingested_at=datetime.now(timezone.utc),
    )


def inv(i, amount, ref, day=1, name="Vendor"):
    return CanonicalTransaction.from_business_fields(
        transaction_id=i, source_system=SourceSystem.PURCHASE_REGISTER, source_record_id=i,
        transaction_date=f"2026-07-{day:02d}", invoice_date=f"2026-07-{day:02d}",
        transaction_type=TransactionType.PURCHASE, amount=Decimal(str(amount)),
        currency="INR", invoice_number=ref, counterparty_name=name,
        ingestion_batch_id="b", ingested_at=datetime.now(timezone.utc),
    )


def test_exact_reference_amount_matches_even_with_small_date_shift():
    result = reconcile([tx("B1", 100, "INV1", 1)], [inv("I1", 100, "INV1", 3)])
    assert result[0].status == "MATCHED"
    assert result[0].tier == "DETERMINISTIC"


def test_reference_with_amount_mismatch_requires_review():
    result = reconcile([tx("B1", 110, "INV1")], [inv("I1", 100, "INV1")])
    assert result[0].status == "REVIEW"
    assert result[0].amount_difference == Decimal("10")


def test_missing_reference_candidate_is_unmatched():
    result = reconcile([tx("B1", 100, "INV1")], [])
    assert result[0].status == "UNMATCHED"


def test_thresholds_are_explicit_configuration():
    config = ReconciliationConfig(\n        date_tolerance_days=1,\n        near_amount_tolerance=Decimal("2.00"),\n        fuzzy_auto_match_threshold=0.81,\n    )
    result = reconcile([tx("B1", 101, "INV1", 2)], [inv("I1", 100, "INV1", 1)], config=config)
    assert result[0].status == "MATCHED"
