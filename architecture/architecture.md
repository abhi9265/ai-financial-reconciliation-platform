# System Architecture

## 1. Objective

Build a reliable financial reconciliation platform that converts heterogeneous accounting and financial records into a common transaction model, reconciles records using an ordered evidence-based matching strategy, identifies anomalies, and routes uncertain decisions for human review and optional AI assistance.

## 2. Source systems

| Source | Example format | Implemented role |
| --- | --- | --- |
| Bank statement | CSV / Excel | transaction feed |
| Purchase register | CSV / Excel | payable-side records |
| Sales register | CSV / Excel | planned adapter |
| Tally export | CSV / Excel | planned adapter |
| Invoice | PDF | planned adapter |
| GST data | JSON | planned adapter |

The implementation uses synthetic data only.

## 3. Logical flow

```
Source Files
    │
    ▼
Ingestion
    ├── source contract validation
    ├── file fingerprint
    ├── batch identity
    └── idempotency keys
    │
    ▼
Bronze Boundary
    │
    ▼
Validation + Normalization
    ├── schema checks
    ├── type normalization
    ├── field standardization
    ├── business-rule checks
    └── lineage
    │
    ▼
Silver Canonical Transactions
    │
    ▼
Reconciliation Engine
    ├── deterministic matching
    ├── conservative fuzzy matching
    └── exception routing
    │
    ▼
Decision + Confidence + Explanation
    ├── matched
    ├── unmatched
    └── human review
    │
    ├── optional AI escalation
    ▼
Anomaly Detection + Evaluation
    │
    ▼
Reports / operational interfaces
```

## 4. Canonical transaction model

The canonical model separates:

### Business meaning
- transaction type
- positive absolute amount
- debit/credit direction

### Dates
- transaction date
- invoice date
- bank value date

These dates are not silently collapsed.

### Counterparty
- name
- type
- GSTIN

### Tax
- taxable amount
- CGST
- SGST
- IGST
- total tax

### Lineage
- source system
- source record ID
- source file name/hash
- source row number
- source schema version

### Idempotency
A deterministic SHA-256 `record_hash` is derived from stable canonical business fields. Volatile ingestion metadata is excluded.

### Batch metadata
`ingestion_batch_id` is deterministically derived from source system, file fingerprint, and schema version.

## 5. Matching strategy

### Tier 1 — Deterministic

Strong evidence includes:
- exact invoice/reference identifier
- exact amount
- date within configured tolerance
- compatible counterparty

A reference match with a material amount mismatch is routed to review instead of being silently accepted.

### Tier 2 — Fuzzy/statistical

Multiple signals can be combined:
- counterparty similarity
- amount difference
- date difference
- reference similarity
- transaction-type compatibility

The current MVP uses standard-library string similarity and a conservative threshold.

### Tier 3 — AI-assisted review

AI is optional and sits behind a provider-neutral reviewer interface. The default implementation does not invent decisions. A future provider can inspect only already-validated ambiguous cases and return a structured recommendation, confidence, rationale, and model identifier.

## 6. Decision contract

Every reconciliation decision contains:
- source record
- candidate record, when available
- matching tier
- signals
- status
- confidence
- explanation

Review cases receive a stable case ID and can be persisted later.

## 7. Reliability principles

The implementation includes:
- immutable/raw ingestion boundary
- deterministic file fingerprinting
- deterministic batch identity
- record hashing
- schema validation
- quarantine-ready quality issue contracts
- explicit lineage
- replayable processing
- automated tests
- evidence-first AI boundary

## 8. Current implementation boundary

The current repository is an executable synthetic-data MVP rather than a production service. Bank and purchase-register adapters are implemented end-to-end. Remaining production work is persistence, API/serving, authentication/authorization, observability, deployment, additional source adapters, and connecting a selected LLM provider behind the existing AI interface.
