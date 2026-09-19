# System Architecture

## 1. Objective

Build a reliable financial reconciliation platform that converts heterogeneous accounting and financial records into a common transaction model, reconciles records using an ordered matching strategy, identifies anomalies, and routes uncertain decisions for human review.

## 2. Source systems

| Source | Example format | Initial role |
| --- | --- | --- |
| Bank statement | CSV / Excel | transaction feed |
| Purchase register | CSV / Excel | payable-side records |
| Sales register | CSV / Excel | receivable-side records |
| Tally export | CSV / Excel | accounting-system records |
| Invoice | PDF | document-level evidence |
| GST data | JSON | tax/reference evidence |

The implementation will use synthetic data only.

## 3. Logical flow

```
Source Files
    │
    ▼
Ingestion
    │
    ├── source validation
    ├── file metadata
    ├── batch identity
    ├── file fingerprint
    └── idempotency
    │
    ▼
Bronze
    │
    ▼
Validation + Normalization
    │
    ├── schema checks
    ├── type normalization
    ├── field standardization
    ├── business-rule checks
    └── quarantine
    │
    ▼
Silver Canonical Transactions
    │
    ▼
Reconciliation Engine
    │
    ├── deterministic matching
    ├── fuzzy/statistical matching
    └── AI escalation for ambiguity
    │
    ▼
Decision + Confidence + Explanation
    │
    ├── matched
    ├── unmatched
    └── human review
    │
    ▼
Anomaly Detection + Reporting
    │
    ▼
Feedback / Evaluation
```

## 4. Canonical transaction model

The canonical model intentionally separates seven concerns:

### Business meaning
- `transaction_type` describes PURCHASE, SALE, PAYMENT, RECEIPT, REFUND, FEE, TAX, JOURNAL, or OTHER.
- `amount` is always a positive absolute amount.
- `amount_direction` represents DEBIT/CREDIT only where source accounting direction exists.

### Dates
- `transaction_date` represents the date of the financial/business event.
- `invoice_date` preserves the invoice document date.
- `value_date` preserves bank settlement/value date.

These dates must not be silently collapsed into one field.

### Counterparty
- `counterparty_name`
- `counterparty_type`
- `counterparty_gstin`

This supports both vendor and customer records without maintaining two competing field sets.

### Tax
- taxable amount
- CGST
- SGST
- IGST
- total tax
- counterparty GSTIN

Tax fields are optional because not every source contains tax information.

### Lineage
- source system
- source record ID
- source file name/hash
- source row number
- source schema version

### Idempotency
A deterministic SHA-256 `record_hash` is derived from stable canonical business fields. Volatile ingestion metadata is excluded.

### Batch metadata
`ingestion_batch_id` identifies the processing run. Batch-level operational statistics will be stored separately from transaction-level records.

The exact schema contract is versioned in `data/schemas/`.

## 5. Matching strategy

The reconciliation engine will use an ordered escalation model:

### Tier 1 — Deterministic

Prefer strong exact evidence such as:
- exact invoice/reference identifier
- exact GSTIN
- exact amount
- date within an explicit tolerance

### Tier 2 — Fuzzy / statistical

Use multiple signals when exact matching is insufficient:
- counterparty similarity
- amount difference
- date difference
- invoice/reference similarity
- transaction type compatibility

### Tier 3 — AI-assisted review

Use AI only for ambiguous candidate pairs. AI output must be structured, validated, and accompanied by an explicit reason and confidence.

AI recommendations do not bypass validation or human approval for configured high-risk cases.

## 6. Decision contract

Every reconciliation decision should be traceable to:
- source record(s)
- candidate record(s)
- matching tier
- signals used
- decision
- confidence
- explanation
- timestamp
- pipeline/batch identifier

## 7. Data-quality and reliability principles

The foundation will include:
- immutable/raw ingestion boundaries
- idempotent batch handling
- deterministic record hashing
- schema validation
- quarantine for invalid records
- explicit lineage
- replayable processing
- automated tests
- clear evidence boundaries

## 8. Implementation boundary

Phase 1 intentionally stops before implementing the AI and reconciliation engine. This keeps the foundation independently testable and prevents the project from becoming an LLM-first demo.

Future phases will extend the same contracts rather than replace them.
