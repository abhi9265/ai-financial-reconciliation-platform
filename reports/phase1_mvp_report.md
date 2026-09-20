# Phase 1 MVP Engineering Report

## Status

**Implemented:** executable end-to-end synthetic reconciliation MVP.

### Delivered components

| Area | Status |
|---|---|
| Canonical transaction contract | Complete |
| Source ingestion contracts | Complete |
| File fingerprinting | Complete |
| Deterministic batch identity | Complete |
| Source normalization | Complete for bank + purchase register |
| Data-quality validation | Complete |
| Record hashing / lineage | Complete |
| Deterministic reconciliation | Complete |
| Conservative fuzzy fallback | Complete |
| Anomaly classification | Complete |
| Human-review case contract | Complete |
| AI escalation interface | Complete, provider-neutral |
| Evaluation metrics | Complete, including ground-truth precision/recall and exception capture |
| CLI | Complete |\n| API boundary | Complete for MVP: FastAPI health/reconcile endpoints |\n| Persistent idempotency | Complete for MVP via SQLite batch/record keys |\n| Review-case persistence | Complete for MVP via SQLite |\n| Structured observability | Complete for MVP via JSON events/timing |
| Unit/integration tests | Added |
| GitHub Actions CI | Configured |
| Persistent database/object storage | Not implemented |
| External LLM provider | Not configured |
| Production API/deployment | Not implemented |

## Synthetic benchmark

The checked-in seed is intentionally structured as a reconciliation benchmark:

- 100 bank transactions
- 95 purchase invoices
- 90 expected auto-matches
- 5 reference-linked amount mismatches routed to review
- 5 bank records without a corresponding purchase record
- 10 expected reconciliation exceptions

The benchmark is a development/evaluation fixture, not a production accuracy claim.

## Architecture decisions

### 1. Evidence before AI

The matching engine evaluates deterministic evidence first: reference number, amount, date tolerance, and counterparty similarity. A strong reference with an amount mismatch is not silently auto-matched.

### 2. AI is an escalation boundary

The AI module is provider-neutral. A future LLM implementation can implement the reviewer protocol without changing ingestion, canonical schemas, or matching logic. The default reviewer never invents a match.

### 3. Idempotency

File SHA-256 fingerprints and deterministic batch IDs make repeated ingestion of the same source/schema combination identifiable. Record-level idempotency combines source identity with canonical record hash.

### 4. Lineage

Canonical records retain source file name/hash, source row number, schema version, and ingestion batch ID.

### 5. Human review

Review cases are first-class objects. They can be persisted or exposed through an API later without changing reconciliation decisions.

## How to run

```bash
python -m pip install -e ".[dev]"
reconcile-demo --data-dir data/synthetic/seed
python -m pytest -q
ruff check .
```

## Production-readiness foundation\n\nStep 5 adds a persistence and service boundary without changing the evidence-first reconciliation contract. SQLite stores batch identities, record-level idempotency keys, and review cases. FastAPI exposes health and reconciliation endpoints. Structured JSON logging records lifecycle events and duration. The default deployment remains intentionally local/MVP-oriented; production would move persistence to a managed database/object store and add authentication, authorization, secrets management, metrics/traces, and deployment infrastructure.\n\n## Evidence limitations

GitHub repository contents were inspected after implementation. Local execution was not available in this session because the runtime could not reach GitHub to download the repository, and the GitHub commit status endpoint currently reports no status entries for the latest documentation commit. Therefore test/CI success is **not claimed** here until GitHub Actions produces a completed run.

## Next production work

The remaining work is deliberately operational rather than architectural: persist Bronze/Silver data, add a real API, connect a selected LLM behind the reviewer protocol, add observability, authentication/authorization, deployment infrastructure, and expand source adapters.
