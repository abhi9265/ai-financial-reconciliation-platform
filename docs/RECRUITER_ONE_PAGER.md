# Recruiter One-Pager

## AI-Powered Financial Reconciliation Platform

**Role signal:** Data Engineering + Backend + AI Systems

### What it does

A production-oriented financial reconciliation platform for heterogeneous bank, invoice and accounting records.

Messy financial data -> validation/normalization -> canonical transactions -> deterministic reconciliation -> matched/review/unmatched -> human + AI review -> auditable output.

### Engineering highlights

- Multi-tenant API with tenant-scoped authorization
- Canonical transaction model with lineage and deterministic identity
- Exact, fuzzy, one-to-many and partial-payment matching
- Candidate blocking and bounded complex matching
- PostgreSQL durable state
- Redis + Celery asynchronous processing
- Object-storage boundary for raw files
- Idempotency and retry-safe job handling
- Review queue and human decision workflow
- Structured audit events
- Prometheus metrics and request-correlated logging
- OpenAI adapter behind a deterministic safety boundary
- Docker production-like runtime
- AWS staging infrastructure-as-code
- CI security and deployment gates

### Measured engineering evidence

| Area | Result |
|---|---:|
| Reconciliation workload | 500K synthetic bank rows |
| Candidate reduction | 99.9926% |
| Full-match recall | 100% |
| Auto-match precision | 100% |
| Partial-payment accuracy | 100% |
| False auto-matches | 0 |
| API load smoke | 1,199 req/s |
| AI safety evaluation | 400 cases |
| Security | Bandit + Trivy + OWASP ZAP |

### Technology

Python · FastAPI · PostgreSQL · Redis · Celery · Pandas · PyArrow · Docker · AWS/Terraform · Prometheus · OpenAI API · GitHub Actions

### Engineering idea

> Deterministic evidence decides. AI escalates ambiguity.

### Evidence boundary

The project uses synthetic/customer-shaped data for engineering validation. It does not claim live customer production usage, production SLAs, live cloud capacity, or permanent live-model accuracy.

### Start here

1. README.md — system overview and evidence
2. docs/ARCHITECTURE.md — system design
3. docs/PROJECT_CASE_STUDY.md — engineering decisions
4. docs/INTERVIEW_CHEATSHEET.md — interview preparation
5. docs/RECRUITER_DEMO.md — five-minute walkthrough
