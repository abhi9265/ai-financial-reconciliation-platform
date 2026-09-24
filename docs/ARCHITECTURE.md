# Production Architecture

## Executive view

This is a multi-tenant, asynchronous financial-data processing system with a deterministic reconciliation core and an advisory AI boundary.

The production design separates:
1. Ingress and authentication
2. Data engineering: validation, normalization and lineage
3. Deterministic reconciliation and decisioning
4. Human + AI review for ambiguity
5. Operations: durable state, audit, metrics, logs and retries

## Logical architecture

~~~text
Tenant
  |
HTTPS / Load Balancer
  |
FastAPI API -----> PostgreSQL (jobs, review, audit)
  |  \
  |   +----------> Object Storage (raw source + lineage)
  |
  +-------------> Redis ---> Celery Worker Pool
                                |
                                +--> validation
                                +--> normalization
                                +--> canonical transactions
                                +--> reconciliation
                                +--> audit / metrics

Ambiguous review cases ---> AI Provider Adapter ---> Human Review
~~~

## Data flow

~~~text
raw source
   -> authenticated ingestion
   -> fingerprint + batch identity + idempotency
   -> validation
   -> source normalization
   -> canonical transaction model + lineage
   -> deterministic reconciliation
   -> matched / unmatched / review
   -> optional AI review
   -> human approval where required
   -> audit + metrics + report
~~~

The raw object remains separate from normalized data so the pipeline can be replayed.

## Reconciliation boundary

The evidence hierarchy is:

~~~text
Deterministic evidence
        |
Conservative fuzzy evidence
        |
Complex / partial matching
        |
Explicit REVIEW
        |
Optional AI assistance
        |
Human approval
~~~

AI is deliberately outside the authoritative matching path.

## Deployment topology

| Layer | Production-oriented component | Scaling model |
|---|---|---|
| Edge | Managed HTTPS load balancer / reverse proxy | Provider-managed |
| API | Containerized FastAPI | Horizontal replicas |
| Queue | Managed Redis | Provider-managed / HA |
| State | Managed PostgreSQL | Vertical + read replicas where justified |
| Object storage | S3-compatible durable object store | Provider-managed |
| Workers | Celery containers | Horizontal worker pool |
| Secrets | Managed secret store | Centralized rotation |
| Observability | Central logs, metrics and alerting | Provider-managed |
| Backups | Managed DB/object-store retention | Scheduled + tested restore |

No specific cloud provider is required by the application architecture.

## Reliability model

The system is designed around idempotent ingestion, tenant-scoped identifiers, deterministic hashes, transactional job state, Celery late acknowledgement, bounded execution, retries/redelivery and durable raw-object storage.

If a worker dies, queued work can be redelivered. If a client retries the same idempotent request, database conflict handling converges on the existing job. If the AI provider is unavailable, deterministic reconciliation remains valid.

## Security boundaries

Tenant identity is established at authentication and carried into storage, jobs, review cases, audit events and rate limits.

Production deployment assumes:
- TLS termination before the application
- secrets supplied by a secret manager
- no production secrets in Git
- tenant-scoped authorization on resource access
- durable audit events
- centralized security/access logs

## Observability contract

Production operations should expose request rate, latency, error rate, queue depth, worker throughput, job duration, retry count, reconciliation outcomes, review backlog, AI latency/failures/cost, database saturation, Redis health and object-storage failures.

Recommended alerts include elevated API 5xx rate, queue age, worker failures, database saturation, repeated AI failures and abnormal review backlog.

## Data-engineering characteristics

The project is intentionally a data-engineering system rather than only an API:
- raw-to-canonical data boundary
- schema validation
- source lineage
- deterministic record identity
- reproducible benchmark generation
- candidate blocking before expensive matching
- bounded complex matching
- partial-payment semantics
- auditable business decisions
- asynchronous processing

## Capacity evidence

The repository contains engineering evidence for a 500K synthetic reconciliation workload, candidate-pair reduction, ground-truth matching metrics, API load smoke testing at 25 concurrent requests and a 400-case offline AI safety evaluation.

These are test-environment measurements, not production SLA or cloud-capacity claims.

## Interview summary

> I separated ingestion, canonicalization and reconciliation so source-specific data problems do not leak into business matching logic. The deterministic engine remains authoritative, while AI is an advisory reviewer for ambiguous cases. PostgreSQL owns durable state, Redis/Celery decouple API traffic from long-running workloads, object storage preserves raw lineage, and tenant-scoped authorization is enforced across persisted resources.
