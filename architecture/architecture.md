# System Architecture

## 1. System objective

The platform reconciles heterogeneous financial records into a canonical transaction model, applies ordered evidence-based matching, detects anomalies, persists explainable decisions, and routes ambiguous cases through human review with optional AI assistance.

The architecture optimizes for:

- deterministic behavior
- replayability
- tenant isolation
- lineage
- idempotency
- asynchronous processing
- operational observability
- controlled AI usage

---

## 2. Runtime architecture

```text
                         ┌─────────────────────┐
                         │  Client / Tenant    │
                         └──────────┬──────────┘
                                    │ HTTPS
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │ auth / validation   │
                         │ request context     │
                         └──────┬──────┬───────┘
                                │      │
                 ┌──────────────┘      └───────────────┐
                 ▼                                     ▼
        ┌─────────────────┐                    ┌───────────────┐
        │ Object Storage  │                    │  PostgreSQL   │
        │ raw tenant data │                    │ jobs / cases  │
        └────────┬────────┘                    │ state / audit │
                 │                             └───────┬───────┘
                 │                                     │
                 └────────────────┐       ┌────────────┘
                                  ▼       ▼
                              ┌─────────────┐
                              │    Redis    │
                              │ broker/cache │
                              └──────┬──────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │    Celery   │
                              │   workers   │
                              └──────┬──────┘
                                     │
                                     ▼
                          ┌────────────────────┐
                          │ Reconciliation     │
                          │ pipeline            │
                          └─────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  ▼                 ▼                 ▼
             Canonical         Anomaly           Review
             decisions         detection         cases
                                                      │
                                                      ▼
                                               Optional AI review
```

The repository supports SQLite/local object storage for development and PostgreSQL/S3-compatible storage for production-style deployments.

---

## 3. End-to-end data flow

```text
Upload
  │
  ├── authenticate tenant
  ├── validate content type
  ├── enforce file size
  └── persist raw object
        │
        ▼
Ingestion boundary
  │
  ├── file fingerprint
  ├── deterministic batch identity
  └── record-level idempotency
        │
        ▼
Validation + normalization
  │
  ├── schema checks
  ├── type coercion
  ├── business-rule validation
  └── lineage enrichment
        │
        ▼
Canonical transactions
        │
        ▼
Reconciliation engine
  │
  ├── deterministic matching
  ├── conservative fuzzy matching
  └── exception routing
        │
        ▼
Decision contract
  │
  ├── MATCHED
  ├── UNMATCHED
  └── HUMAN_REVIEW
        │
        ├── anomaly classification
        └── optional AI escalation
                 │
                 ▼
       audit + metrics + report
```

---

## 4. Source and canonical data model

Current end-to-end source adapters:

- bank statements
- purchase registers

Planned adapter boundaries:

- sales registers
- Tally exports
- invoice/PDF ingestion
- GST/JSON sources

All sources converge on the canonical transaction contract.

### Canonical business fields

- transaction type
- absolute amount
- debit/credit direction
- transaction date
- invoice date
- bank value date
- counterparty
- GSTIN
- taxable amount
- CGST / SGST / IGST
- total tax

### Lineage fields

- source system
- source record ID
- source file name
- source file hash
- source row number
- source schema version
- ingestion batch ID

### Deterministic identity

`record_hash` is a SHA-256 hash over stable canonical business fields. Volatile ingestion metadata is excluded so replaying the same source data produces the same identity.

---

## 5. Reconciliation strategy

### Tier 1 — deterministic evidence

The engine first evaluates strong signals:

- exact invoice/reference identifier
- amount compatibility
- date tolerance
- counterparty compatibility
- transaction-type compatibility

A material amount mismatch is deliberately routed to review instead of being silently auto-matched.

### Tier 2 — conservative fuzzy evidence

Candidate scoring can combine:

- counterparty similarity
- amount difference
- date difference
- reference similarity
- transaction compatibility

The implementation favors precision and explicit exceptions over maximizing automatic match volume.

### Tier 3 — AI-assisted review

AI is an escalation mechanism.

Only already-validated ambiguous cases are eligible for AI review. The provider interface returns structured review evidence such as:

- recommendation
- confidence
- rationale
- model metadata

The AI output does not override the deterministic reconciliation contract or silently create an automatic match.

---

## 6. Multi-tenant isolation

Tenant context is propagated through:

```text
API credential
    ↓
tenant identity
    ↓
object key namespace
    ↓
job state
    ↓
review cases
    ↓
audit events
    ↓
rate-limit key
```

Example object namespace:

```text
tenants/{tenant_id}/raw/{source_system}/{filename}
```

Authorization is enforced server-side. Tenant A's credentials cannot be used to retrieve tenant B's job or review state.

---

## 7. Asynchronous execution

The API supports two execution modes:

### Lightweight mode

```text
FastAPI → persistent job → background task
```

Useful for development and single-instance deployments.

### Distributed mode

```text
FastAPI
   ↓
PostgreSQL job record
   ↓
Redis broker
   ↓
Celery worker
   ↓
reconciliation pipeline
   ↓
PostgreSQL result
```

Celery configuration includes:

- JSON-only task serialization
- late acknowledgement
- prefetch multiplier of 1
- task-start tracking
- bounded hard and soft execution times
- broker connection retry on startup

This makes API latency independent of reconciliation execution time and provides a path to horizontal worker scaling.

---

## 8. Reliability and idempotency

The pipeline is designed for safe retries.

Key mechanisms:

- immutable/raw object boundary
- SHA-256 file fingerprints
- deterministic batch IDs
- canonical record hashes
- persisted idempotency keys
- persistent job states
- tenant-scoped identifiers
- late worker acknowledgements

The goal is to make retries **safe and observable**, not merely possible.

---

## 9. Observability and auditability

The HTTP boundary generates:

- request ID
- method
- route
- status
- latency

The application records:

- reconciliation outcomes
- job lifecycle transitions
- AI review metadata
- tenant-scoped audit events
- benchmark/evaluation summaries

Operational interfaces:

- `GET /health`
- `GET /ready`
- `GET /metrics`
- `GET /v1/audit`

The local JSONL audit implementation is suitable for development. A cloud deployment should route audit events to durable centralized storage with retention and access controls.

---

## 10. Security boundaries

Implemented controls include:

- API-key authentication
- tenant-bound authorization
- constant-time key comparison
- safe tenant ID validation
- CSV-only upload validation
- 10 MiB upload limit
- object-key path traversal protection
- repository data-path validation
- security response headers
- tenant-scoped request throttling
- dependency vulnerability scanning
- Docker build validation
- secrets excluded from source control

Production infrastructure should additionally provide TLS, managed secrets, network controls, centralized security monitoring, and backup/restore procedures.

---

## 11. Storage model

### PostgreSQL

Durable application state:

- ingestion batches
- idempotency records
- review cases
- reconciliation jobs
- job results

### Object storage

Raw uploaded files:

```text
tenants/
  └── {tenant_id}/
      └── raw/
          ├── bank/
          └── purchase_register/
```

### Redis

Operational messaging:

- Celery broker
- distributed job dispatch
- shared runtime coordination where enabled

---

## 12. Evaluation boundary

The synthetic benchmark contains:

- 100 bank transactions
- 95 purchase invoices
- 90 expected matches
- 5 amount-mismatch review cases
- 5 unmatched cases

The benchmark is deterministic and reproducible. It validates pipeline behavior and regression safety; it is **not** evidence of production financial accuracy.

---

## 13. Architectural principles

1. **Evidence before intelligence** — deterministic evidence precedes AI.
2. **Exceptions are first-class data** — uncertainty is persisted, not hidden.
3. **Lineage is part of the data model** — every decision can be traced to source evidence.
4. **Idempotency is explicit** — retries should not create duplicate business state.
5. **Tenant boundaries are enforced server-side** — isolation is not a UI concern.
6. **Work is asynchronous when it should be** — API requests do not own long-running reconciliation.
7. **Observability is part of the system** — logs, metrics and audit events are designed alongside business logic.
8. **Synthetic data protects confidentiality** — no customer financial data or secrets are required for the repository.
