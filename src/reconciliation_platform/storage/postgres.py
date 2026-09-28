"""PostgreSQL persistence for production deployments."""
from __future__ import annotations

from typing import Iterable

import psycopg
from psycopg.types.json import Jsonb

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
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    source_system TEXT NOT NULL,
                    file_fingerprint TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    UNIQUE(tenant_id, source_system, file_fingerprint, schema_version)
                );

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    source_system TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    record_hash TEXT NOT NULL,
                    batch_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reconciliation_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    bank_key TEXT NOT NULL,
                    purchase_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result JSONB,
                    error TEXT,
                    idempotency_key TEXT,
                    UNIQUE(tenant_id, idempotency_key)
                );

                CREATE TABLE IF NOT EXISTS review_cases (
                    case_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL DEFAULT 'default',
                    record_id TEXT NOT NULL,
                    candidate_record_id TEXT,
                    reason TEXT NOT NULL,
                    confidence DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    resolved_at TIMESTAMPTZ,
                    resolution_note TEXT
                );
                """
            )
            batch_columns = {
                row[0]
                for row in connection.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'ingestion_batches'"
                ).fetchall()
            }
            if "tenant_id" not in batch_columns:
                connection.execute("ALTER TABLE ingestion_batches ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'")
                connection.execute(
                    "ALTER TABLE ingestion_batches DROP CONSTRAINT IF EXISTS ingestion_batches_source_system_file_fingerprint_schema_version_key"
                )
                connection.execute(
                    "ALTER TABLE ingestion_batches ADD CONSTRAINT ingestion_batches_tenant_source_fingerprint_key UNIQUE (tenant_id, source_system, file_fingerprint, schema_version)"
                )
            columns = {
                row[0]
                for row in connection.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'review_cases'"
                ).fetchall()
            }
            if "tenant_id" not in columns:
                connection.execute(
                    "ALTER TABLE review_cases ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'default'"
                )
            if "status" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
            if "resolved_at" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN resolved_at TIMESTAMPTZ")
            if "resolution_note" not in columns:
                connection.execute("ALTER TABLE review_cases ADD COLUMN resolution_note TEXT")
            connection.commit()

    def register_batch(
        self,
        *,
        batch_id: str,
        source_system: str,
        file_fingerprint: str,
        schema_version: str,
        created_at: str,
        tenant_id: str = "default",
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO ingestion_batches
                (batch_id, tenant_id, source_system, file_fingerprint, schema_version, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (batch_id, tenant_id, source_system, file_fingerprint, schema_version, created_at),
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

    def save_review_cases(self, cases: Iterable[ReviewCase], *, tenant_id: str = "default") -> int:
        inserted = 0
        with self._connect() as connection:
            for case in cases:
                cursor = connection.execute(
                    """
                    INSERT INTO review_cases
                    (case_id, tenant_id, record_id, candidate_record_id, reason, confidence, created_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'open')
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        f"{tenant_id}:{case.case_id}",
                        tenant_id,
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

    def list_review_cases(self, *, tenant_id: str, status: str, limit: int, offset: int) -> tuple[list[dict], int]:
        with self._connect() as connection:
            if status == "all":
                total = int(connection.execute(
                    "SELECT COUNT(*) FROM review_cases WHERE tenant_id = %s", (tenant_id,)
                ).fetchone()[0])
                rows = connection.execute(
                    "SELECT case_id, record_id, candidate_record_id, reason, confidence, created_at, status, resolved_at, resolution_note "
                    "FROM review_cases WHERE tenant_id = %s ORDER BY created_at ASC, case_id ASC LIMIT %s OFFSET %s",
                    (tenant_id, limit, offset),
                ).fetchall()
            else:
                total = int(connection.execute(
                    "SELECT COUNT(*) FROM review_cases WHERE tenant_id = %s AND status = %s",
                    (tenant_id, status),
                ).fetchone()[0])
                rows = connection.execute(
                    "SELECT case_id, record_id, candidate_record_id, reason, confidence, created_at, status, resolved_at, resolution_note "
                    "FROM review_cases WHERE tenant_id = %s AND status = %s "
                    "ORDER BY created_at ASC, case_id ASC LIMIT %s OFFSET %s",
                    (tenant_id, status, limit, offset),
                ).fetchall()
            keys = ["case_id", "record_id", "candidate_record_id", "reason", "confidence", "created_at", "status", "resolved_at", "resolution_note"]
            return [dict(zip(keys, row, strict=True)) for row in rows], total

    def get_review_case(self, case_id: str, *, tenant_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT case_id, record_id, candidate_record_id, reason, confidence, created_at, status, resolved_at, resolution_note "
                "FROM review_cases WHERE case_id = %s AND tenant_id = %s",
                (case_id, tenant_id),
            ).fetchone()
            if row is None:
                return None
            keys = ["case_id", "record_id", "candidate_record_id", "reason", "confidence", "created_at", "status", "resolved_at", "resolution_note"]
            return dict(zip(keys, row, strict=True))

    def resolve_review_case(self, case_id: str, *, tenant_id: str, status: str, note: str | None) -> bool:
        from datetime import datetime, timezone
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE review_cases SET status = %s, resolved_at = %s, resolution_note = %s "
                "WHERE case_id = %s AND tenant_id = %s AND status = 'open'",
                (status, datetime.now(timezone.utc), note, case_id, tenant_id),
            )
            connection.commit()
            return cursor.rowcount == 1

    def review_case_count(self, *, tenant_id: str | None = None) -> int:
        with self._connect() as connection:
            if tenant_id is None:
                return int(connection.execute("SELECT COUNT(*) FROM review_cases").fetchone()[0])
            return int(
                connection.execute(
                    "SELECT COUNT(*) FROM review_cases WHERE tenant_id = %s",
                    (tenant_id,),
                ).fetchone()[0]
            )


    def create_job(self, *, job_id: str, tenant_id: str, bank_key: str, purchase_key: str, idempotency_key: str | None = None) -> str:
        with self._connect() as connection:
            if idempotency_key:
                inserted = connection.execute(
                    "INSERT INTO reconciliation_jobs "
                    "(job_id, tenant_id, bank_key, purchase_key, status, idempotency_key) VALUES (%s, %s, %s, %s, 'queued', %s) "
                    "ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING job_id",
                    (job_id, tenant_id, bank_key, purchase_key, idempotency_key),
                ).fetchone()
                if inserted is None:
                    existing = connection.execute(
                        "SELECT job_id FROM reconciliation_jobs WHERE tenant_id = %s AND idempotency_key = %s",
                        (tenant_id, idempotency_key),
                    ).fetchone()
                    connection.commit()
                    return existing[0]
            else:
                connection.execute(
                    "INSERT INTO reconciliation_jobs "
                    "(job_id, tenant_id, bank_key, purchase_key, status, idempotency_key) VALUES (%s, %s, %s, %s, 'queued', %s)",
                    (job_id, tenant_id, bank_key, purchase_key, idempotency_key),
                )
            connection.commit()
            return job_id

    def get_job(self, job_id: str, *, tenant_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT job_id, tenant_id, status, result, error FROM reconciliation_jobs "
                "WHERE job_id = %s AND tenant_id = %s",
                (job_id, tenant_id),
            ).fetchone()
            if row is None:
                return None
            return {
                "job_id": row[0], "tenant_id": row[1], "status": row[2],
                "result": row[3], "error": row[4],
            }

    def save_reconciliation_results(  # pragma: no coverself, *, job_id: str, tenant_id: str, decisions: Iterable[object]) -> int:
        from datetime import datetime, timezone
        import hashlib
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS reconciliation_results (
                result_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, tenant_id TEXT NOT NULL,
                record_id TEXT NOT NULL, candidate_record_id TEXT, status TEXT NOT NULL,
                match_tier TEXT NOT NULL, confidence DOUBLE PRECISION NOT NULL, explanation TEXT NOT NULL,
                amount_difference TEXT, created_at TIMESTAMPTZ NOT NULL,
                UNIQUE(job_id, tenant_id, record_id))""")
            inserted = 0
            now = datetime.now(timezone.utc)
            for decision in decisions:
                result_id = hashlib.sha256(f"{job_id}:{tenant_id}:{decision.bank_record_id}".encode()).hexdigest()[:24]
                cursor = connection.execute(
                    """INSERT INTO reconciliation_results
                    (result_id, job_id, tenant_id, record_id, candidate_record_id, status, match_tier, confidence, explanation, amount_difference, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (job_id, tenant_id, record_id) DO NOTHING""",
                    (result_id, job_id, tenant_id, decision.bank_record_id, decision.counterparty_record_id,
                     decision.status, decision.tier, decision.confidence, decision.explanation,
                     str(decision.amount_difference) if decision.amount_difference is not None else None, now),
                )
                inserted += cursor.rowcount
            connection.commit()
            return inserted

    def list_reconciliation_results(  # pragma: no coverself, *, job_id: str, tenant_id: str, status: str = "all", limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
        with self._connect() as connection:
            if status == "all":
                total = connection.execute("SELECT COUNT(*) FROM reconciliation_results WHERE job_id=%s AND tenant_id=%s", (job_id, tenant_id)).fetchone()[0]
                rows = connection.execute("SELECT result_id, record_id, candidate_record_id, status, match_tier, confidence, explanation, amount_difference, created_at FROM reconciliation_results WHERE job_id=%s AND tenant_id=%s ORDER BY record_id LIMIT %s OFFSET %s", (job_id, tenant_id, limit, offset)).fetchall()
            else:
                total = connection.execute("SELECT COUNT(*) FROM reconciliation_results WHERE job_id=%s AND tenant_id=%s AND status=%s", (job_id, tenant_id, status)).fetchone()[0]
                rows = connection.execute("SELECT result_id, record_id, candidate_record_id, status, match_tier, confidence, explanation, amount_difference, created_at FROM reconciliation_results WHERE job_id=%s AND tenant_id=%s AND status=%s ORDER BY record_id LIMIT %s OFFSET %s", (job_id, tenant_id, status, limit, offset)).fetchall()
            columns = ["result_id","record_id","candidate_record_id","status","match_tier","confidence","explanation","amount_difference","created_at"]
            return [dict(zip(columns, row, strict=True)) for row in rows], int(total)

    def save_reconciliation_report(self, *, job_id: str, tenant_id: str, report: dict) -> None:
        from datetime import datetime, timezone
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_reports (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    report JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            connection.execute(
                "INSERT INTO reconciliation_reports (job_id, tenant_id, report, created_at) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (job_id) DO UPDATE SET tenant_id = EXCLUDED.tenant_id, report = EXCLUDED.report, created_at = EXCLUDED.created_at",
                (job_id, tenant_id, Jsonb(report), datetime.now(timezone.utc)),
            )
            connection.commit()

    def get_reconciliation_report(self, job_id: str, *, tenant_id: str) -> dict | None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_reports (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    report JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT report, created_at FROM reconciliation_reports WHERE job_id = %s AND tenant_id = %s",
                (job_id, tenant_id),
            ).fetchone()
            if row is None:
                return None
            return {"report": row[0], "created_at": row[1]}

    def update_job(self, job_id: str, *, tenant_id: str, status: str, result: dict | None = None, error: str | None = None) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE reconciliation_jobs SET status = %s, result = %s, error = %s "
                "WHERE job_id = %s AND tenant_id = %s",
                (status, Jsonb(result) if result is not None else None, error, job_id, tenant_id),
            )
            connection.commit()
