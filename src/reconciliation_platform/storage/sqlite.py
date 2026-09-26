"""SQLite persistence for batches, idempotency keys, and review cases."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from reconciliation_platform.decisioning.review import ReviewCase
from reconciliation_platform.ingestion.batch import compute_idempotency_key
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


class SQLiteStore:
    """Small transactional store suitable for the MVP and local deployment."""

    def __init__(self, path: str | Path = "data/reconciliation.db") -> None:
        self.path = str(path)
        self._memory_connection: sqlite3.Connection | None = None
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        if self.path == ":memory:":
            if self._memory_connection is None:
                self._memory_connection = sqlite3.connect(":memory:")
                self._memory_connection.row_factory = sqlite3.Row
            return self._memory_connection
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS ingestion_batches (
                    batch_id TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    file_fingerprint TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_system, file_fingerprint, schema_version)
                );

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    resolved_at TEXT,
                    resolution_note TEXT
                );

                CREATE TABLE IF NOT EXISTS review_cases (\n                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    case_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    candidate_record_id TEXT,
                    reason TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(review_cases)")}
            if "tenant_id" not in columns:
                connection.execute(
                    "ALTER TABLE review_cases ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                )
            if "status" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
            if "resolved_at" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN resolved_at TEXT")
            if "resolution_note" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN resolution_note TEXT")

    def register_batch(
        self,
        *,
        batch_id: str,
        source_system: str,
        file_fingerprint: str,
        schema_version: str,
        created_at: str,
    ) -> bool:
        """Persist a batch. Return False when the same batch was already registered."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO ingestion_batches
                (batch_id, source_system, file_fingerprint, schema_version, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (batch_id, source_system, file_fingerprint, schema_version, created_at),
            )
            return cursor.rowcount == 1

    def register_transactions(
        self,
        transactions: Iterable[CanonicalTransaction],
        *,
        batch_id: str,
        created_at: str,
    ) -> tuple[int, int]:
        """Persist record-level idempotency keys and return (inserted, duplicates)."""
        inserted = 0
        duplicates = 0
        with self._connect() as connection:
            for tx in transactions:
                key = compute_idempotency_key(
                    tx.source_system, tx.source_record_id, tx.record_hash
                )
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO idempotency_records
                    (idempotency_key, source_system, source_record_id, record_hash, batch_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        key,
                        tx.source_system.value,
                        tx.source_record_id,
                        tx.record_hash,
                        batch_id,
                        created_at,
                    ),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    duplicates += 1
        return inserted, duplicates

    def save_review_cases(self, cases: Iterable[ReviewCase], *, tenant_id: str = "default") -> int:
        inserted = 0
        with self._connect() as connection:
            for case in cases:
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO review_cases
                    (case_id, tenant_id, record_id, candidate_record_id, reason, confidence, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'open')
                    """,
                    (
                        f"{tenant_id}:{case.case_id}",
                        tenant_id,
                        case.record_id,
                        case.candidate_record_id,
                        case.reason,
                        case.confidence,
                        case.created_at.isoformat(),
                    ),
                )
                inserted += cursor.rowcount
        return inserted

    def list_review_cases(self, *, tenant_id: str, status: str, limit: int, offset: int) -> tuple[list[dict], int]:
        with self._connect() as connection:
            where = "tenant_id = ?"
            params: list[object] = [tenant_id]
            if status != "all":
                where += " AND status = ?"
                params.append(status)
            total = int(connection.execute(f"SELECT COUNT(*) FROM review_cases WHERE {where}", params).fetchone()[0])
            rows = connection.execute(
                f"SELECT case_id, record_id, candidate_record_id, reason, confidence, created_at, status, resolved_at, resolution_note "
                f"FROM review_cases WHERE {where} ORDER BY created_at ASC, case_id ASC LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
            return [dict(row) for row in rows], total

    def get_review_case(self, case_id: str, *, tenant_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_id, record_id, candidate_record_id, reason, confidence, created_at, status, resolved_at, resolution_note "
                "FROM review_cases WHERE case_id = ? AND tenant_id = ?",
                (case_id, tenant_id),
            ).fetchone()
            return dict(row) if row else None

    def resolve_review_case(self, case_id: str, *, tenant_id: str, status: str, note: str | None) -> bool:
        from datetime import datetime, timezone
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE review_cases SET status = ?, resolved_at = ?, resolution_note = ? "
                "WHERE case_id = ? AND tenant_id = ? AND status = 'open'",
                (status, datetime.now(timezone.utc).isoformat(), note, case_id, tenant_id),
            )
            return cursor.rowcount == 1

    def review_case_count(self, *, tenant_id: str | None = None) -> int:
        with self._connect() as connection:
            if tenant_id is None:
                return int(connection.execute("SELECT COUNT(*) FROM review_cases").fetchone()[0])
            return int(connection.execute("SELECT COUNT(*) FROM review_cases WHERE tenant_id = ?", (tenant_id,)).fetchone()[0])


    def create_job(self, *, job_id: str, tenant_id: str, bank_key: str, purchase_key: str, idempotency_key: str | None = None) -> str:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    bank_key TEXT NOT NULL,
                    purchase_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT,
                    idempotency_key TEXT,
                    UNIQUE(tenant_id, idempotency_key)
                )
                """
            )
            columns = {row[1] for row in connection.execute("PRAGMA table_info(reconciliation_jobs)")}
            if "idempotency_key" not in columns:
                connection.execute("ALTER TABLE reconciliation_jobs ADD COLUMN idempotency_key TEXT")
            connection.execute(
                "INSERT OR IGNORE INTO reconciliation_jobs "
                "(job_id, tenant_id, bank_key, purchase_key, status, idempotency_key) VALUES (?, ?, ?, ?, 'queued', ?)",
                (job_id, tenant_id, bank_key, purchase_key, idempotency_key),
            )
            if idempotency_key:
                existing = connection.execute(
                    "SELECT job_id FROM reconciliation_jobs WHERE tenant_id = ? AND idempotency_key = ?",
                    (tenant_id, idempotency_key),
                ).fetchone()
                if existing:
                    return existing[0]
            return job_id

    def get_job(self, job_id: str, *, tenant_id: str) -> dict | None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    bank_key TEXT NOT NULL,
                    purchase_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    error TEXT
                )
                """
            )
            row = connection.execute(
                "SELECT job_id, tenant_id, bank_key, purchase_key, status, result, error "
                "FROM reconciliation_jobs WHERE job_id = ? AND tenant_id = ?",
                (job_id, tenant_id),
            ).fetchone()
            if row is None:
                return None
            import json
            return {
                "job_id": row[0], "tenant_id": row[1], "status": row[4],
                "result": json.loads(row[5]) if row[5] else None, "error": row[6],
            }

    def update_job(self, job_id: str, *, tenant_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
        with self._connect() as connection:
            import json
            connection.execute(
                "UPDATE reconciliation_jobs SET status = ?, result = ?, error = ? "
                "WHERE job_id = ? AND tenant_id = ?",
                (status, json.dumps(result) if result is not None else None, error, job_id, tenant_id),
            )
