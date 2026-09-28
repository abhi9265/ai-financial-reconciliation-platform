# Database Migrations

The repository now has explicit Alembic migrations for durable production schema changes.

## Commands

    alembic upgrade head
    DATABASE_URL='postgresql://user:password@host:5432/reconciliation' alembic upgrade head
    alembic current
    alembic history
    alembic downgrade -1

The baseline includes ingestion batches, idempotency records, reconciliation jobs, review cases, durable reports, and individual reconciliation results.

Application startup retains defensive CREATE TABLE IF NOT EXISTS compatibility for the zero-cost/local runtime, but production deployments should run alembic upgrade head as an explicit deployment step before application rollout.

Migration validation is part of CI.
