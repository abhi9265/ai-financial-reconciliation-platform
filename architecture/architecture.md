# System Architecture

## 1. Objective

Build a reliable financial reconciliation platform that converts heterogeneous accounting and financial records into a common transaction model, reconciles records using an ordered matching strategy, identifies anomalies, and routes uncertain decisions for human review.

## 2. Source systems

Initial source types:

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

The canonical model is intended to isolate downstream logic from source-specific schemas.

Core fields:

- transaction identity: `transaction_id`, `source_system`, `source_record_id`
- dates: `transaction_date`, `value_date`
- amount: `debit`, `credit`, `amount`, `currency`
- description: `description`, `reference_number`
- counterparty: `vendor_name`, `vendor_gstin`
- invoice context: `invoice_number`, `invoice_date`
- tax context: `taxable_amount`, `cgst`, `sgst`, `igst`, `total_tax`
- accounting context: `account_name`, `bank_account`
- ingestion/audit metadata: `ingestion_batch_id`, `source_file`, `source_row_number`, `record_hash`, `ingested_at`

The exact schema contract will be versioned in `data/schemas/`.

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
- vendor similarity
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
