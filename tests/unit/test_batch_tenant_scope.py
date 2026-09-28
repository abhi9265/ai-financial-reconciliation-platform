from reconciliation_platform.ingestion.batch import compute_batch_id
from reconciliation_platform.models.canonical_transaction import SourceSystem
from reconciliation_platform.storage.sqlite import SQLiteStore


def test_batch_identity_is_tenant_scoped():
    fingerprint = "a" * 64
    first = compute_batch_id(SourceSystem.BANK, fingerprint, "1.0", "tenant_a")
    second = compute_batch_id(SourceSystem.BANK, fingerprint, "1.0", "tenant_b")
    assert first != second


def test_sqlite_batches_allow_same_source_file_for_different_tenants(tmp_path):
    store = SQLiteStore(tmp_path / "batches.db")
    fingerprint = "b" * 64
    first_id = compute_batch_id(SourceSystem.BANK, fingerprint, "1.0", "tenant_a")
    second_id = compute_batch_id(SourceSystem.BANK, fingerprint, "1.0", "tenant_b")

    assert store.register_batch(
        batch_id=first_id,
        tenant_id="tenant_a",
        source_system="bank",
        file_fingerprint=fingerprint,
        schema_version="1.0",
        created_at="2026-09-28T00:00:00+00:00",
    )
    assert store.register_batch(
        batch_id=second_id,
        tenant_id="tenant_b",
        source_system="bank",
        file_fingerprint=fingerprint,
        schema_version="1.0",
        created_at="2026-09-28T00:00:00+00:00",
    )
    assert not store.register_batch(
        batch_id=first_id,
        tenant_id="tenant_a",
        source_system="bank",
        file_fingerprint=fingerprint,
        schema_version="1.0",
        created_at="2026-09-28T00:00:00+00:00",
    )
