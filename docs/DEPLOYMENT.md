## Zero-cost deployment path

The repository can now run a **production-like deployment locally for ₹0**.

This is the recommended path while the project has a hard no-spend constraint. It exercises the deployment shape without creating AWS, Azure, GCP or other billable resources.

### Local production topology

~~~text
                    localhost:8080
                          |
                    Nginx edge
                          |
                    FastAPI API
                       /     \
                      /       \
             PostgreSQL      Redis
                                |
                           Celery worker
                                |
                         local object volume
~~~

Run:

~~~bash
export POSTGRES_PASSWORD='choose-a-local-secret'
export RECONCILIATION_API_KEY='choose-a-local-secret'
bash scripts/run_zero_cost_production.sh
~~~

The script builds the application image locally, starts the complete stack, waits for /ready, and keeps services running until interrupted.

Endpoints:

~~~text
http://localhost:8080/health
http://localhost:8080/ready
http://localhost:8080/openapi.json
~~~

Nothing in this workflow provisions cloud infrastructure or requires a paid service.

### What this proves

The zero-cost deployment gate validates:

- production Docker image build
- multi-container startup
- PostgreSQL readiness
- Redis readiness
- API readiness
- reverse-proxy routing
- authentication path
- worker startup
- restart policies
- read-only application containers
- dropped Linux capabilities
- no-new-privileges runtime configuration
- clean Compose shutdown

GitHub Actions runs the same validation automatically. It is an application/deployment validation environment, **not a public production environment**.

## Production cloud path later

When spending is explicitly approved, the existing AWS staging Terraform can be promoted to a real environment. That future deployment would require an AWS account, DNS, TLS certificate, secrets and managed services.

**Do not run the AWS Terraform while the project is under the zero-spend constraint.**

## Existing managed-cloud blueprint

The repository still contains infra/aws/staging/ as infrastructure-as-code. It is intentionally not applied as part of the zero-cost path.

The managed architecture remains:

~~~text
Internet
   |
HTTPS Load Balancer
   |
FastAPI replicas
   |       |       |
   |       |       +--> Managed PostgreSQL
   |       +----------> Managed Redis
   +------------------> S3-compatible object storage

Celery worker replicas <--- Redis queue
~~~

No live cloud resources are claimed.

## Deployment sequence for a future paid environment

1. Build an immutable image from a tagged commit.
2. Push the image to a private registry.
3. Provision managed PostgreSQL, Redis, object storage and HTTPS ingress.
4. Configure secrets through a secret manager.
5. Apply controlled database migrations.
6. Deploy API and worker replicas separately.
7. Run /health and /ready smoke tests.
8. Verify metrics, logs, backups and alerts.
9. Monitor rollout and retain the previous image for rollback.
10. Exercise restore and rollback procedures.

## Current deployment claim

> **Application: production-like deployment verified locally and in CI. Cloud: deployment blueprint only; no billable cloud resources have been provisioned.**

The repository proves deployment mechanics without pretending that a local environment is customer-facing production.

# Production Deployment Guide

## Scope

This document defines the path from the repository's Docker/Compose topology to a managed production environment.

The repository currently proves deployment readiness, not a live public production deployment. No cloud resources, customer data, production SLA, RPO/RTO or external penetration test are claimed.

## Target topology

~~~text
Internet
   |
HTTPS Load Balancer
   |
FastAPI replicas
   |       |       |
   |       |       +--> Managed PostgreSQL
   |       +----------> Managed Redis
   +------------------> S3-compatible object storage

Celery worker replicas <--- Redis queue
~~~

## Deployment sequence

### 1. Build an immutable image

Build from a tagged commit and retain:
- Git commit SHA
- application version
- image digest
- build timestamp

Do not deploy an untracked local image.

### 2. Provision managed dependencies

Create PostgreSQL, Redis, S3-compatible object storage, a secret manager, centralized logs/metrics and HTTPS ingress.

### 3. Configure secrets

Inject API credentials, database credentials and optional AI/object-store credentials through the platform secret manager. Never commit production secrets or print them in CI logs.

### 4. Initialize database state

Initialize the PostgreSQL schema as a controlled release step. For a real deployment, use explicit migration tooling rather than changing schema automatically from every API replica.

### 5. Deploy API and workers separately

Run API replicas behind HTTPS. Run Celery workers as a separately scalable service.

Scale API from request rate/latency and workers from queue depth/oldest-job age/throughput.

### 6. Configure durable object storage

Use a tenant-scoped layout such as:
~~~text
tenants/{tenant_id}/raw/{source_system}/{file}
~~~

Enable encryption, lifecycle/retention controls and least-privilege service access.

### 7. Configure observability

Collect structured logs, request IDs, API latency/errors, queue depth, worker/job metrics, database health and AI provider metrics.

## Environment model

### Local
Docker Compose provides PostgreSQL, Redis, API, Celery worker and local object storage.

### Staging
Use managed dependencies, separate credentials, HTTPS, centralized logs and synthetic/customer-shaped test data only.

### Production
Use managed PostgreSQL with backups, managed Redis, durable object storage, managed secrets, TLS, centralized observability, least-privilege identities and a tested restore process.

## Pre-release checklist

- [ ] CI green
- [ ] Docker image builds
- [ ] Compose configuration validates
- [ ] PostgreSQL readiness passes
- [ ] Redis readiness passes
- [ ] API health/readiness passes
- [ ] authentication enabled
- [ ] secrets injected by secret manager
- [ ] object storage durable and tenant-scoped
- [ ] request IDs present in logs
- [ ] metrics collected
- [ ] backups enabled
- [ ] restore procedure exercised
- [ ] rollback path documented
- [ ] representative workload benchmark completed
- [ ] security review completed
- [ ] live AI evaluation completed if AI is enabled

## Rollback

Deploy immutable application images by version.

Rollback should route traffic away from the new release, restore the previous known-good image, preserve PostgreSQL job/audit state, inspect queued jobs for compatibility, verify /ready and monitor error rate and queue health.

Database changes should remain backward compatible across release boundaries whenever possible.

## Cloud mapping

| Concern | AWS-style example | Azure-style example |
|---|---|---|
| Container runtime | ECS/Fargate or AKS/ECS equivalent | Container Apps / AKS |
| PostgreSQL | RDS PostgreSQL | Azure Database for PostgreSQL |
| Redis | ElastiCache | Azure Cache for Redis |
| Object storage | S3 | Blob Storage |
| Secrets | Secrets Manager | Key Vault |
| Observability | CloudWatch | Azure Monitor / Application Insights |
| HTTPS ingress | ALB / API Gateway | Application Gateway / Front Door |

These are examples, not completed infrastructure.

## Current repository claim

> Production-oriented deployment architecture and containerized runtime implemented; external production deployment intentionally not claimed.


## Phase 2 staging implementation

The repository now includes an AWS staging implementation under `infra/aws/staging/`. It provisions the managed runtime described above: RDS PostgreSQL, TLS-enabled ElastiCache Redis, S3 object storage, ECS Fargate API/worker services, HTTPS ALB, Secrets Manager, CloudWatch logs and Route 53.

The staging application is configured with `DATABASE_HOST`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_NAME` and `DATABASE_PORT`; the runtime builds a correctly escaped PostgreSQL URL when `DATABASE_URL` is not supplied. This keeps database credentials out of the task definition's plaintext environment.

Staging deployment remains an operator action because it requires an AWS account, certificate, DNS zone and credentials. The infrastructure is validated in CI with Terraform format/validation and a container configuration smoke check.
