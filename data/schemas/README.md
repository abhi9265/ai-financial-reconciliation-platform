# Canonical Transaction Contract

The canonical transaction is the contract between source-specific ingestion and downstream reconciliation.

## Design goals

1. Preserve source traceability.
2. Normalize common financial concepts without assuming every source has every field.
3. Keep optional source attributes nullable.
4. Support deterministic idempotency and replay.
5. Keep reconciliation decisions separate from source facts.

## Required fields

- `transaction_id`
- `source_system`
- `source_record_id`
- `transaction_date`
- `amount`
- `currency`
- `transaction_type`
- `ingestion_batch_id`
- `record_hash`
- `ingested_at`

## Source traceability

Every normalized record retains source system, source record identifier, source file, source row number, ingestion batch, and record hash.

## Amount semantics

`amount` is the normalized transaction value used downstream. `debit` and `credit` preserve directional information when available.

## Tax semantics

Tax fields are nullable because bank transactions and some accounting exports do not contain tax-level information.

GSTIN validation at this layer is structural only; a syntactically valid GSTIN is not proof of entity ownership.

## Reconciliation boundary

Fields such as `match_decision`, `match_confidence`, and `review_status` belong to downstream reconciliation contracts, not the canonical source transaction.

See `canonical_transaction.schema.json` for the machine-readable contract and `canonical_transaction.example.json` for a representative record.
