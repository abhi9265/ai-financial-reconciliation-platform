# AI-Powered Financial Reconciliation Platform

An engineering-focused financial reconciliation platform for Indian SMEs and CA firms.

The system converts heterogeneous financial records into a common transaction model, applies evidence-first reconciliation, identifies exceptions, and creates traceable review cases. AI is intentionally positioned as an escalation layer rather than the foundation.

## Current MVP

The repository now contains an executable synthetic-data MVP covering:

- source-specific ingestion contracts
- SHA-256 file fingerprinting and deterministic batch identity
- source-to-canonical normalization
- lineage and record hashing
- business/data-quality validation
- deterministic reconciliation with conservative fuzzy fallback
- anomaly classification
- human-review case generation
- automated unit + integration tests
- FastAPI API boundary with health and reconciliation endpoints
- SQLite persistence for batch registration, record-level idempotency, and review cases
- structured JSON logging with timing instrumentation
- ground-truth evaluation with precision/recall/exception-capture metrics
- optional OpenAI Responses API reviewer for ambiguous cases only
- API-key authentication and data-root path validation
- environment-driven runtime configuration with no committed secrets
- GitHub Actions CI
- CLI execution

## Workflow

```
Source Files
    ↓
Ingest + Contract Validation
    ↓
Batch Identity / Fingerprint
    ↓
Normalize
    ↓
Canonical Transactions
    ↓
Reconciliation
    ├── Deterministic
    ├── Fuzzy
    └── Review
    ↓
Anomaly Detection
    ↓
Human Review Cases
    ↓
Evaluation / Reporting
```

## Synthetic benchmark

The current seed contains 100 bank transactions and 95 purchase invoices. The integration benchmark expects:

| Outcome | Count |
| --- | ---: |
| Auto matched | 90 |
| Review: referenced invoice amount mismatch | 5 |
| Unmatched: invoice absent | 5 |

The benchmark is deliberately synthetic and reproducible. It is not a production accuracy claim.

## Run locally

```bash
python -m pip install -e ".[dev]"
reconcile-demo --data-dir data/synthetic/seed
```

Or:

```bash
python -m pytest -q
ruff check .
```

## Architecture

See [architecture/architecture.md](architecture/architecture.md) for the system design and evidence boundaries.

## Repository structure

```text
ai-financial-reconciliation-platform/
├── architecture/
├── data/
│   ├── schemas/
│   └── synthetic/
├── reports/
├── src/
│   └── reconciliation_platform/
│       ├── anomaly/
│       ├── decisioning/
│       ├── ingestion/
│       ├── models/
│       ├── normalization/
│       ├── reconciliation/
│       └── validation/
├── tests/
│   ├── integration/
│   └── unit/
├── pyproject.toml
└── .github/workflows/
```

## Engineering principles

### AI is not the source of truth
Strong deterministic evidence is evaluated first. Ambiguous cases are represented explicitly for review.

### Every decision is traceable
Decisions retain source IDs, candidate IDs, matching tier, signals, confidence, explanation, and pipeline metadata.

### Idempotency is designed in
Raw file fingerprints, batch IDs, and canonical record hashes make retries and duplicate processing detectable.

### Synthetic data only
No customer financial data, credentials, secrets, or PII should be committed.

## Report

See [reports/phase1_mvp_report.md](reports/phase1_mvp_report.md) for the current implementation report, benchmark expectations, engineering decisions, and limitations.


## AI reviewer

The deterministic reconciliation engine remains authoritative. When `AI_PROVIDER=openai`, only records already classified as `REVIEW` are sent to the OpenAI Responses API. The adapter requests a strict structured response containing a recommendation, confidence, and rationale; the API returns this as review evidence and does not convert the AI recommendation into an automatic match. The default `AI_PROVIDER=none` keeps the system fully deterministic and offline.

OpenAI API credentials must be supplied through the runtime environment and are never committed to the repository. See `.env.example` for configuration names.

## API security

The reconciliation and storage endpoints require `X-API-Key` by default. Set `API_KEY_REQUIRED=false` only for local development/testing. The API also restricts reconciliation input paths to the repository's `data/` root, reducing the risk of arbitrary local filesystem access.


## Production deployment

The repository includes a production-oriented container path.

Run locally with Docker Compose:

    cp .env.example .env
    # Set RECONCILIATION_API_KEY in .env
    docker compose up --build

The API container uses PostgreSQL by default through DATABASE_URL. SQLite remains available as a local fallback when DATABASE_URL is unset.

Endpoints:
- GET /health — liveness check; no authentication required.
- GET /ready — readiness check; verifies storage connectivity.
- POST /reconcile — authenticated reconciliation execution.
- GET /storage/health — authenticated persistence check.

### Secrets

Keep RECONCILIATION_API_KEY and OPENAI_API_KEY outside source control. The reconciliation API key is intentionally separate from the OpenAI credential. In a real deployment, inject both from the platform's secret manager rather than committing a .env file.

### Production limitations

The current API still accepts a repository-local data_dir. The container path is therefore deployment-ready for a controlled internal workload, but a multi-tenant production service should replace this with authenticated file uploads/object storage and tenant-scoped authorization. TLS termination, rate limiting, distributed tracing, and metrics are also deployment-layer concerns.


## Tenant-aware file ingestion

Production-facing ingestion is available at `POST /v1/reconcile`.

Send:
- `X-API-Key` for API authentication when enabled.
- `X-Tenant-ID` for tenant isolation.
- `bank_file` as a CSV upload.
- `purchase_file` as a CSV upload.

Uploaded files are stored under a tenant-scoped object key such as `tenants/acme_01/raw/bank/...`. The configured object-store backend can be local filesystem storage for development or Amazon S3 for production. The reconciliation engine processes a temporary materialized copy, so clients never provide a server filesystem path.

Each uploaded file is limited to 10 MiB and only CSV files are accepted.

Tenant IDs are restricted to safe alphanumeric, underscore, and hyphen identifiers. Review-case persistence is tenant-scoped, preventing identical source record IDs in separate tenants from sharing a review namespace.

Example:

    curl -X POST http://localhost:8000/v1/reconcile \
      -H "X-API-Key: $RECONCILIATION_API_KEY" \
      -H "X-Tenant-ID: acme_01" \
      -F "bank_file=@data/synthetic/seed/bank_transactions.csv" \
      -F "purchase_file=@data/synthetic/seed/purchase_invoices.csv"

For production S3, set `OBJECT_STORE=s3`, `S3_BUCKET`, and AWS credentials through the deployment platform's secret/identity mechanism.


### Tenant authorization

For multi-tenant deployments, set `TENANT_API_KEYS` as a comma-separated mapping of tenant IDs to unique API keys:

```text
TENANT_API_KEYS=acme_01:replace-with-secret-a,other_01:replace-with-secret-b
```

The `/v1/reconcile` endpoint requires `X-Tenant-ID` and, when this mapping is configured, verifies that the supplied `X-API-Key` is authorized for that tenant. A valid key for one tenant cannot be used to access another tenant.

Do not commit real API keys. Store production credentials in the deployment secret manager.
