from reconciliation_platform.ingestion.batch import compute_batch_id, compute_file_fingerprint, compute_idempotency_key
from reconciliation_platform.models.canonical_transaction import SourceSystem

def test_file_fingerprint_and_batch_id_are_deterministic():
    content = b"hello"
    fp = compute_file_fingerprint(content)
    assert fp == compute_file_fingerprint(content)
    assert compute_batch_id(SourceSystem.BANK, fp, "1.0") == compute_batch_id(SourceSystem.BANK, fp, "1.0")

def test_idempotency_key_changes_with_record_identity():
    a = compute_idempotency_key(SourceSystem.BANK, "A", "hash-a")
    b = compute_idempotency_key(SourceSystem.BANK, "B", "hash-a")
    assert a != b
