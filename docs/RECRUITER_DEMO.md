# Recruiter / Interview Demo

## 60-second project pitch

> I built a multi-tenant financial reconciliation platform for messy bank, invoice and accounting data. I did not make the LLM the decision engine. I built a deterministic reconciliation pipeline with exact, fuzzy, one-to-many and partial-payment matching, then placed AI behind a review boundary for ambiguous cases. The system uses a canonical transaction model, object-storage lineage, PostgreSQL for durable state, Redis/Celery for asynchronous processing, tenant isolation, audit events and CI-based scale and safety evidence.

## Five-minute demo flow

### 1. Business problem
Explain that financial records arrive from heterogeneous systems, exact equality is insufficient, and false auto-matches are more dangerous than explicit review.

### 2. Architecture
Open docs/ARCHITECTURE.md and point to the API, raw object storage, canonical transaction layer, deterministic reconciliation, PostgreSQL, Redis/Celery and human/AI review boundary.

### 3. Data-engineering depth
Explain:
~~~text
raw source -> validation -> normalization -> canonical transaction
          -> lineage + deterministic identity
          -> reconciliation
~~~
Highlight candidate blocking before expensive matching and bounded complex matching for large candidate sets.

### 4. Evidence

| Evidence | Measured result |
|---|---:|
| Synthetic reconciliation scale | 500K cases |
| Candidate reduction | 99.9926% |
| Full-match recall | 100% |
| Auto-match precision | 100% |
| Partial-payment accuracy | 100% |
| False auto-matches | 0 |
| API load smoke | 1,199 req/s |
| API requests | 1,000 |
| API concurrency | 25 |
| Offline AI safety cases | 400 |

Always describe these as test-environment measurements.

### 5. AI boundary

Use this line:

> AI does not decide whether a financial transaction is safe to auto-match. It receives already-validated ambiguous review cases, returns structured evidence, and unsafe recommendations are downgraded to human review.

Live model accuracy/latency/cost still requires an external provider credential.

## High-value interview questions

**Why not let the LLM reconcile everything?**

Because deterministic evidence is reproducible and auditable. AI is useful for semantic ambiguity but should not bypass the safety boundary.

**Why PostgreSQL + Redis + Celery?**

PostgreSQL owns durable state. Redis provides queue infrastructure. Celery keeps long-running reconciliation outside the request lifecycle and allows independent worker scaling.

**Why a canonical model?**

It prevents source adapters from implementing their own reconciliation semantics. Source-specific parsing ends at normalization.

**How did you approach scale?**

First reduce the candidate search space with blocking. Then bound expensive complex matching. Finally validate with measured synthetic workloads rather than theoretical throughput claims.

**How do you prevent duplicate jobs?**

Tenant-scoped idempotency keys plus database-level conflict handling make concurrent retries converge on the same job.

**How would you deploy this?**

Containerize API and worker separately, put API replicas behind HTTPS, use managed PostgreSQL/Redis/object storage, inject secrets from a secret manager and scale workers from queue depth.

**What is not production-proven yet?**

External cloud deployment, customer-shaped workload validation, live AI accuracy/latency/cost and third-party penetration testing. The repository intentionally does not pretend those steps are complete.

## Resume bullets

- Built a multi-tenant financial reconciliation platform using FastAPI, PostgreSQL, Redis/Celery, object storage and deterministic matching.
- Designed a canonical transaction layer with source lineage, deterministic identity, tenant isolation and idempotent asynchronous processing.
- Implemented exact, fuzzy, one-to-many and partial-payment reconciliation with candidate blocking and measured 500K-case synthetic scale evidence.
- Integrated an advisory AI review boundary with structured outputs and offline safety evaluation, keeping deterministic evidence authoritative.
- Added production-oriented CI, security checks, container validation, observability, auditability and API load testing.

## LinkedIn project description

**AI-Powered Financial Reconciliation Platform**

Production-oriented Data Engineering + AI system for reconciling bank, invoice and accounting records. Built around a deterministic matching core, canonical transaction model, tenant isolation, asynchronous processing and an advisory AI review layer. Includes measured 500K-case reconciliation evidence, API load testing, auditability, security checks and Docker-based deployment architecture.
