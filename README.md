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
