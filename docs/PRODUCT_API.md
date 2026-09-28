# Product API Workflow

The public API is versioned under `/v1`. The workflow is intentionally small: upload financial inputs, track the reconciliation job, inspect the tenant review queue, and record a human decision.

## Authentication and tenancy

Tenant endpoints require:

- `X-Tenant-ID`
- `X-API-Key` when tenant API keys are configured

Every review lookup and decision is scoped by tenant. A case from another tenant is not addressable through the same API credentials.

## Reconciliation flow

### 1. Upload and reconcile

`POST /v1/reconcile`

Multipart fields:

- `bank_file`
- `purchase_file`

The response contains deterministic reconciliation totals and the persisted review count.

### 2. Async processing

`POST /v1/reconcile/async`

Use `Idempotency-Key` to make client retries safe. The response returns a job ID.

### 3. Track the job

`GET /v1/reconcile/jobs/{job_id}`

Job states are:

- `queued`
- `running`
- `succeeded`
- `failed`

### 4. Review queue

`GET /v1/reviews?status=open&limit=50&offset=0`

Supported status filters:

- `open`
- `approved`
- `rejected`
- `all`

The response includes a stable total, offset/limit and tenant-scoped case records.

### 5. Resolve a review case

`POST /v1/reviews/{case_id}/decision`

Example:

~~~json
{
  "action": "approve",
  "note": "Reviewed against source evidence"
}
~~~

Supported actions are `approve` and `reject`. A case can only transition once from `open` to a terminal review state.

The action records an append-only audit event. It does **not** rewrite the deterministic reconciliation evidence; the human decision is recorded as a workflow outcome.

## Error contract

HTTP and validation failures use a consistent envelope:

~~~json
{
  "error": {
    "code": "HTTP_ERROR",
    "message": "review case not found",
    "request_id": "..."
  }
}
~~~

Validation failures use `VALIDATION_ERROR` and include structured validation details.

## OpenAPI

FastAPI exposes the generated OpenAPI contract at `/docs` and `/openapi.json`. The API is grouped into reconciliation, reviews, audit and operations tags.

## Design boundary

The review API is a workflow boundary, not a second matching engine. Deterministic reconciliation remains authoritative; AI can assist only inside the existing review/escalation boundary.


## Phase 8 — Upload-to-Reconciliation Workflow

The reconciliation API now supports a validated upload-to-job boundary. `POST /v1/reconcile/async` validates both source contracts before creating a job, records deterministic batch IDs, and returns source row counts. Completed jobs can be read through `GET /v1/reconcile/jobs/{job_id}/report`, which is tenant-scoped and returns the persisted reconciliation result. The deterministic engine remains authoritative; AI remains advisory for review cases.


## Persisted reconciliation reports

Completed asynchronous reconciliation jobs persist their final tenant-scoped report in the configured SQLite or PostgreSQL store. `GET /v1/reconcile/jobs/{job_id}/report` reads that persisted report rather than reconstructing it from transient worker state. Reports include reconciliation counts, AI-review metadata, review-case persistence count, tenant and source-object metadata, and are only accessible within the owning tenant.
