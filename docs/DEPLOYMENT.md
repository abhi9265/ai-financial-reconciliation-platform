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
