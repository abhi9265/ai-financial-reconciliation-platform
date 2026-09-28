"""Baseline schema for explicit production migrations."""
from alembic import op

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS ingestion_batches (batch_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', source_system TEXT NOT NULL, file_fingerprint TEXT NOT NULL, schema_version TEXT NOT NULL, created_at TIMESTAMP NOT NULL, UNIQUE(tenant_id, source_system, file_fingerprint, schema_version))""")
    op.execute("""CREATE TABLE IF NOT EXISTS idempotency_records (idempotency_key TEXT PRIMARY KEY, source_system TEXT NOT NULL, source_record_id TEXT NOT NULL, record_hash TEXT NOT NULL, batch_id TEXT NOT NULL, created_at TIMESTAMP NOT NULL)""")
    op.execute("""CREATE TABLE IF NOT EXISTS reconciliation_jobs (job_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, bank_key TEXT NOT NULL, purchase_key TEXT NOT NULL, status TEXT NOT NULL, result TEXT, error TEXT, idempotency_key TEXT, UNIQUE(tenant_id, idempotency_key))""")
    op.execute("""CREATE TABLE IF NOT EXISTS review_cases (case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL DEFAULT 'default', record_id TEXT NOT NULL, candidate_record_id TEXT, reason TEXT NOT NULL, confidence DOUBLE PRECISION NOT NULL, created_at TIMESTAMP NOT NULL, status TEXT NOT NULL DEFAULT 'open', resolved_at TIMESTAMP, resolution_note TEXT)""")
    op.execute("""CREATE TABLE IF NOT EXISTS reconciliation_reports (job_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, report TEXT NOT NULL, created_at TIMESTAMP NOT NULL)""")
    op.execute("""CREATE TABLE IF NOT EXISTS reconciliation_results (result_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, tenant_id TEXT NOT NULL, record_id TEXT NOT NULL, candidate_record_id TEXT, status TEXT NOT NULL, match_tier TEXT NOT NULL, confidence DOUBLE PRECISION NOT NULL, explanation TEXT NOT NULL, amount_difference TEXT, created_at TIMESTAMP NOT NULL, UNIQUE(job_id, tenant_id, record_id))""")
def downgrade() -> None:
    for table in ("reconciliation_results","reconciliation_reports","review_cases","reconciliation_jobs","idempotency_records","ingestion_batches"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
