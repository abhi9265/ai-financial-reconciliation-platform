"""PostgreSQL persistence for production deployments."""
from __future__ import annotations

from typing import Iterable

import psycopg

from reconciliation_platform.decisioning.review import ReviewCase
from reconciliation_platform.ingestion.batch import compute_idempotency_key
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


class PostgresStore:
    """Transactional store for production deployments."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._initialize()

    def _connect(self):
        return psycopg.connect(self.database_url)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_batches (
                    batch_id TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    file_fingerprint TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    UNIQUE(source_system, file_fingerprint, schema_version)
                );

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_cases (
                    case_id TEXT PRIMARY KEY,
                    record_id TEXT NOT NULL,
                    candidate_record_id TEXT,
                    reason TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                );
                """
            )
            connection.commit()

    def register_batch(
        self,
        *,
        batch_id: str,
        source_system: str,
        file_fingerprint: str,
        schema_version: str,
        created_at: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_batches
                (batch_id, source_system, file_fingerprint, schema_version, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (batch_id, source_system, file_fingerprint, schema_version, created_at),
            )
            connection.commit()
            return cursor.rowcount == 1

    def register_transactions(
        self,
        transactions: Iterable[CanonicalTransaction],
        *,
        batch_id: str,
        created_at: str,
    ) -> tuple[int, int]:
        inserted = 0
        duplicates = 0
        with self._connect() as connection:
            for tx in transactions:
                key = compute_idempotency_key(
                    tx.source_system, tx.source_record_id, tx.record_hash
                )
                cursor = connection.execute(
                    """
                    INSERT INTO idempotency_records
                    (idempotency_key, source_system, source_record_id, record_hash, batch_id, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
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
            connection.commit()
        return inserted, duplicates

    def save_review_cases(self, cases: Iterable[ReviewCase]) -> int:
        inserted = 0
        with self._connect() as connection:
            for case in cases:
                cursor = connection.execute(
                    """
                    INSERT INTO review_cases
                    (case_id, record_id, candidate_record_id, reason, confidence, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        case.case_id,
                        case.record_id,
                        case.candidate_record_id,
                        case.reason,
                        case.confidence,
                        case.created_at,
                    ),
                )
                inserted += cursor.rowcount
            connection.commit()
        return inserted

    def review_case_count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM review_cases").fetchone()[0])
