# Phase 1 MVP Engineering Report

## Scope completed

The repository now contains an executable synthetic financial reconciliation MVP covering:

1. Source ingestion contracts
2. File fingerprinting and deterministic batch identity
3. Source-to-canonical normalization
4. Canonical business validation
5. Lineage metadata
6. Deterministic reconciliation with controlled fuzzy fallback
7. Exception/anomaly classification
8. Human-review case generation
9. Automated unit and integration tests
10. CI configuration

## Seed-data result

The pipeline is designed to run against `data/synthetic/seed`.

Expected seed characteristics:
- 100 bank transactions
- 95 purchase invoices
- 90 transactions auto-matched
- 5 transactions routed to review because the referenced invoice amount differs
- 5 transactions remain unmatched because corresponding purchase records are absent
- 10 reconciliation anomalies are surfaced from those exceptions

## Engineering decisions

### AI boundary

No LLM is required for the core path. Deterministic evidence is evaluated first. Ambiguous records are explicitly represented as review cases so an AI layer can be added later without changing the canonical or reconciliation contracts.

### Idempotency

Raw file content is fingerprinted with SHA-256. Batch identity is derived from source system, file fingerprint, and schema version. Record-level idempotency can additionally be derived from source record identity and canonical record hash.

### Lineage

Every normalized record retains source file name/hash, source row number, schema version, and ingestion batch ID.

### Evidence

The integration test encodes the expected result of the current synthetic seed. This is a reproducible benchmark, not a production performance claim.

## Known limitations

- Only bank and purchase-register adapters are implemented in this MVP.
- Bronze storage is represented by the source boundary; no object-store/database persistence is required yet.
- Fuzzy matching uses a standard-library string similarity implementation and is intentionally conservative.
- AI-assisted review, persistent human approval, APIs, observability, and deployment are deferred to the next phase.
