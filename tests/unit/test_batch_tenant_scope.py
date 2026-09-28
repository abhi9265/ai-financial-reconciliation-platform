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


def test_sqlite_migrates_legacy_batches_to_default_tenant(tmp_path):
    import sqlite3

    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE ingestion_batches (batch_id TEXT PRIMARY KEY, source_system TEXT NOT NULL, file_fingerprint TEXT NOT NULL, schema_version TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(source_system, file_fingerprint, schema_version))"
        )
        connection.execute(
            "INSERT INTO ingestion_batches VALUES (?, ?, ?, ?, ?)",
            ("legacy-1", "bank", "c" * 64, "1.0", "2026-09-28T00:00:00+00:00"),
        )

    store = SQLiteStore(path)
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT tenant_id, batch_id FROM ingestion_batches WHERE batch_id = ?",
            ("legacy-1",),
        ).fetchone()
    assert row == ("default", "legacy-1")
    assert not store.register_batch(
        batch_id="legacy-1",
        tenant_id="default",
        source_system="bank",
        file_fingerprint="c" * 64,
        schema_version="1.0",
        created_at="2026-09-28T00:00:00+00:00",
    )


def test_batch_identity_default_scope_is_stable():
    fingerprint = "d" * 64
    assert compute_batch_id(SourceSystem.BANK, fingerprint, "1.0") == compute_batch_id(
        SourceSystem.BANK, fingerprint, "1.0", "default"
    )
