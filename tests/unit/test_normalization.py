from datetime import datetime, timezone
from decimal import Decimal
from reconciliation_platform.models.canonical_transaction import SourceSystem, TransactionType, AmountDirection
from reconciliation_platform.normalization.context import NormalizationContext
from reconciliation_platform.normalization.normalizer import normalize_row

def ctx(source):
    return NormalizationContext(source, "source.csv", "a"*64, "1.0", "batch-1", datetime(2026, 8, 1, tzinfo=timezone.utc))

def test_bank_normalization_preserves_lineage_and_semantics():
    row = {"transaction_id":"BANK-1","transaction_date":"2026-07-01","value_date":"2026-07-01","debit":"100.00","credit":"","amount":"100.00","narration":"Vendor A","reference":"INV-1","account_number":"XXXX"}
    tx = normalize_row(row, context=ctx(SourceSystem.BANK), row_number=2)
    assert tx.transaction_type is TransactionType.PAYMENT
    assert tx.amount_direction is AmountDirection.DEBIT
    assert tx.amount == Decimal("100.00")
    assert tx.source_row_number == 2
    assert tx.record_hash and len(tx.record_hash) == 64

def test_purchase_normalization_maps_tax_fields():
    row = {"invoice_record_id":"REC-1","invoice_number":"INV-1","invoice_date":"2026-07-01","vendor_name":"Vendor A","gstin":"24ABCDE1234F1Z5","taxable_value":"100.00","cgst":"9.00","sgst":"9.00","igst":"0.00","total":"118.00"}
    tx = normalize_row(row, context=ctx(SourceSystem.PURCHASE_REGISTER), row_number=2)
    assert tx.transaction_type is TransactionType.PURCHASE
    assert tx.total_tax == Decimal("18.00")
    assert tx.amount == Decimal("118.00")

def test_bank_credit_export_with_debit_artifact_uses_effective_credit():
    row = {"transaction_id":"BANK-1","transaction_date":"2026-07-01","value_date":"2026-07-01","debit":"100.00","credit":"101.00","amount":"101.00","narration":"Vendor A","reference":"INV-1","account_number":"XXXX"}
    tx = normalize_row(row, context=ctx(SourceSystem.BANK), row_number=2)
    assert tx.amount == Decimal("101.00")
    assert tx.debit is None and tx.credit == Decimal("101.00")
