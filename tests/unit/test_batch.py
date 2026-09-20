from reconciliation_platform.ingestion.batch import (
    compute_batch_id,
    compute_file_fingerprint,
    compute_idempotency_key,
    find_duplicate_idempotency_keys,
)
from reconciliation_platform.models.canonical_transaction import SourceSystem


def test_file_fingerprint_and_batch_id_are_deterministic():
    content = b"hello"
    fingerprint = compute_file_fingerprint(content)
    assert fingerprint == compute_file_fingerprint(content)
    assert compute_batch_id(SourceSystem.BANK, fingerprint, "1.0") == compute_batch_id(SourceSystem.BANK, fingerprint, "1.0")


def test_idempotency_key_changes_with_record_identity():
    assert compute_idempotency_key(SourceSystem.BANK, "B1", "hash") != compute_idempotency_key(SourceSystem.BANK, "B2", "hash")


def test_duplicate_idempotency_keys_are_detected():
    assert find_duplicate_idempotency_keys(["a", "b", "a"]) == {"a"}
