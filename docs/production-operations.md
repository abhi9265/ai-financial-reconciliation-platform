# Production Operations Runbook

This repository is production-oriented, but a real deployment still requires an operator-controlled environment, secrets, backups, monitoring and recovery testing.

## Required production controls

- Use managed PostgreSQL or an operator-managed PostgreSQL cluster.
- Set POSTGRES_PASSWORD, RECONCILIATION_API_KEY, and tenant credentials through a secret manager.
- Prefer S3-compatible object storage for uploaded financial files rather than local object storage.
- Keep Redis highly available when distributed rate limiting or Celery is enabled.
- Terminate TLS at the ingress/load balancer.
- Restrict database, Redis and object-store network access to the application network.
- Do not commit secrets or production data.

## Health and monitoring

- /health checks process liveness.
- /ready checks storage readiness.
- /metrics exposes application counters.
- Structured request and reconciliation events are emitted through the observability layer.
- Alert on repeated 5xx responses, failed reconciliation jobs, queue backlog, storage failures, database saturation and abnormal latency.

## Backup

Use:
DATABASE_URL='postgresql://...' BACKUP_DIR=./backups ./scripts/backup_postgres.sh

The script writes a PostgreSQL custom-format dump and SHA-256 checksum.

For cloud deployments, copy backups to durable, access-controlled storage and apply retention/immutability according to the organization's recovery policy.

## Restore drill

Use a non-production database first:
DATABASE_URL='postgresql://...' BACKUP_FILE=./backups/reconciliation-<timestamp>.dump CONFIRM_RESTORE=YES ./scripts/restore_postgres.sh

Validate row counts, tenant isolation, audit records, reconciliation jobs and representative reconciliation outcomes after restore.

## Recovery objectives

Define and test RPO/RTO before calling a deployment production-ready. The repository does not invent an RPO/RTO value because that depends on the deployment architecture and business requirements.

## Security assessment

CI dependency auditing and container checks are automated. A production security assessment/penetration test remains an external deployment gate and must be performed against the deployed environment.
