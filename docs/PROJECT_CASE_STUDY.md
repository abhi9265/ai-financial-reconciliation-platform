# Project Case Study

## AI-Powered Financial Reconciliation Platform

### Problem

Bank statements, invoices, Tally/accounting exports and GST-style records differ in identifiers, naming, dates, payment structure and data quality. The challenge is to automate useful matches without turning ambiguity into silent financial errors.

### Design goal

Build a multi-tenant platform with deterministic reconciliation, canonical financial data, explainable outcomes, asynchronous processing, tenant isolation, auditability, controlled AI assistance, and measurable scale/security evidence.

## Architecture

Financial sources -> ingestion/validation -> canonical transaction model -> candidate blocking -> deterministic matching.

MATCHED / REVIEW / UNMATCHED.

REVIEW -> AI advisory -> human decision -> audit.

FastAPI -> PostgreSQL; Redis -> Celery workers; object storage preserves raw data.

## Key engineering decisions

### 1. Normalize before reconciling

Source adapters convert heterogeneous records into one canonical contract. This keeps source-specific parsing out of business matching logic.

### 2. Evidence before intelligence

The hierarchy is deterministic evidence, conservative fuzzy evidence, bounded complex matching, explicit review, optional AI assistance, and human approval.

### 3. Block candidates before expensive matching

A naive many-to-many comparison grows rapidly. Candidate blocking reduces the search space before scoring.

### 4. Bound complex matching

Large candidate sets cannot trigger unrestricted combinations. The implementation caps complex candidates and routes oversized cases to an explicit safe outcome instead of risking runaway computation.

### 5. Separate API and worker execution

Synchronous API traffic and long-running reconciliation jobs have different scaling characteristics. PostgreSQL owns durable state while Redis/Celery handles distributed execution.

### 6. Treat tenant isolation as a data boundary

Tenant identity is carried through jobs, objects, review cases, audit events and rate limits rather than being enforced only by the UI.

## Evidence

The repository contains controlled CI/test evidence for 500K synthetic bank rows, 99.9926% candidate-pair reduction, 100% full-match recall, 100% auto-match precision, 100% partial-payment accuracy, zero false auto-matches, 1,000 API requests at 25-way concurrency, 1,199 req/s, and 400 adversarial offline AI safety cases.

These measurements are not customer-production SLAs.

## Deployment story

### Today, at zero cost

A production-like Docker Compose deployment runs Nginx, FastAPI, PostgreSQL, Redis, Celery and local object storage. GitHub Actions starts the complete stack and validates readiness, health, edge routing and authentication.

### Future managed deployment

The AWS infrastructure-as-code blueprint maps the same application to HTTPS ALB, ECS Fargate API/worker services, RDS PostgreSQL, TLS Redis, S3, Secrets Manager, CloudWatch and Route 53.

No live cloud deployment is claimed until real infrastructure is provisioned and verified.

## What I would improve next

1. Add explicit schema migration tooling.
2. Add source-specific production parsers/connectors.
3. Run live AI evaluation with controlled provider credentials.
4. Validate with approved customer-shaped datasets.
5. Exercise disaster recovery and restore on managed infrastructure.
6. Add deeper product workflows around reconciliation reports and review operations.

## Interview takeaway

> Control the data contract -> reduce the search space -> make decisions explainable -> isolate tenants -> decouple workloads -> measure the system -> keep AI behind a safety boundary.
