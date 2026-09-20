# API Examples

Base URL:

```
http://localhost:8000
```

## Health

```bash
curl http://localhost:8000/health
```

Expected:

```json
{"status":"ok"}
```

## Synchronous tenant reconciliation

Configure:

```bash
export API_KEY="your-tenant-api-key"
export TENANT_ID="acme_01"
```

Then:

```bash
curl -X POST http://localhost:8000/v1/reconcile \
  -H "X-API-Key: $API_KEY" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -F "bank_file=@data/synthetic/seed/bank_transactions.csv" \
  -F "purchase_file=@data/synthetic/seed/purchase_invoices.csv"
```

The response contains the reconciliation summary, AI-review metadata, tenant ID, object keys, and persisted review-case count.

## Asynchronous reconciliation

```bash
curl -X POST http://localhost:8000/v1/reconcile/async \
  -H "X-API-Key: $API_KEY" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -F "bank_file=@data/synthetic/seed/bank_transactions.csv" \
  -F "purchase_file=@data/synthetic/seed/purchase_invoices.csv"
```

Example response shape:

```json
{
  "job_id": "…",
  "tenant_id": "acme_01",
  "status": "queued",
  "objects": {
    "bank": "tenants/acme_01/raw/bank/bank_transactions.csv",
    "purchase_register": "tenants/acme_01/raw/purchase_register/purchase_invoices.csv"
  }
}
```

Poll the job:

```bash
curl "http://localhost:8000/v1/reconcile/jobs/$JOB_ID" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Possible states:

```
queued → running → succeeded
                    ↘ failed
```

## Audit events

```bash
curl "http://localhost:8000/v1/audit?limit=100" \
  -H "X-API-Key: $API_KEY" \
  -H "X-Tenant-ID: $TENANT_ID"
```

## Metrics

```bash
curl http://localhost:8000/metrics
```

## Readiness

```bash
curl http://localhost:8000/ready
```

## Production queue mode

For distributed workers:

```bash
JOB_QUEUE=celery
RATE_LIMIT_BACKEND=redis
REDIS_URL=redis://redis:6379/0
```

Docker Compose starts PostgreSQL, Redis, the API, and a Celery worker.
