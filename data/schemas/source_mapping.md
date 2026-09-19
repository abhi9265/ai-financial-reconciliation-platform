# Source-to-Canonical Mapping

Source-specific schemas terminate at ingestion. Downstream reconciliation consumes canonical records.

## 1. Transaction type

`transaction_type` describes the **business event**, not the accounting direction.

| Business event | transaction_type |
|---|---|
| Supplier purchase | PURCHASE |
| Customer sale | SALE |
| Outgoing bank payment | PAYMENT |
| Incoming bank receipt | RECEIPT |
| Reversal/refund | REFUND |
| Bank/service charge | FEE |
| Tax payment/receipt | TAX |
| Accounting journal | JOURNAL |
| Unclassified event | OTHER |

`amount_direction` describes debit/credit direction where the source provides it. It is intentionally separate from `transaction_type`.

## 2. Debit / credit representation

`amount` is always a positive absolute value.

For sources that expose accounting direction:
- `amount_direction=DEBIT` and `debit=amount`
- `amount_direction=CREDIT` and `credit=amount`

The opposite amount field remains null.

For sources where debit/credit is not meaningful, `amount_direction`, `debit`, and `credit` may be null.

This prevents business semantics such as PURCHASE or SALE from being incorrectly coupled to bank-account debit/credit direction.

## 3. Dates

| Field | Meaning |
|---|---|
| transaction_date | Date of the financial/business event represented by the source record |
| invoice_date | Date printed/recorded on the invoice document |
| value_date | Bank settlement/value date when supplied by a bank source |

A source record can therefore contain different transaction and invoice dates without overwriting either value.

## 4. Counterparty

Use a generalized counterparty model instead of separate vendor/customer columns:
- `counterparty_name`
- `counterparty_type`
- `counterparty_gstin`

Examples:
- supplier invoice → VENDOR
- customer invoice → CUSTOMER
- bank charge → BANK
- GST payment → TAX_AUTHORITY

This gives the reconciliation engine one consistent field for entity matching.

## 5. GST

The canonical model stores normalized tax components:
- `taxable_amount`
- `cgst`
- `sgst`
- `igst`
- `total_tax`
- `counterparty_gstin`

GST data is supporting tax/reference evidence. It is not treated as the sole source of truth for a financial transaction.

Tax fields are nullable because bank transactions and some accounting records have no tax detail.

## 6. Source lineage

Every normalized record must retain enough information to trace it back to its source:
- `source_system`
- `source_record_id`
- `source_file_name`
- `source_file_hash`
- `source_row_number`
- `source_schema_version`

These fields are operational lineage, not reconciliation features.

## 7. Record hashing

`record_hash` is a SHA-256 hash represented as 64 lowercase hexadecimal characters.

It must be calculated from a **stable canonical business payload**, excluding volatile fields such as:
- `transaction_id`
- `ingested_at`
- `ingestion_batch_id`

This allows the same source record to produce the same hash across retries while still permitting batch-level lineage.

The exact canonicalization algorithm will be implemented and tested before ingestion is considered idempotent.

## 8. Batch metadata

`ingestion_batch_id` identifies the ingestion batch/run that produced the normalized record.

At minimum, the batch layer will also track:
- source system
- source file name
- source file hash
- ingestion start/end timestamps
- records received
- records accepted
- records quarantined

A later batch metadata contract will make retries and replay auditable.

## Invariants

- Amounts are represented in the source currency and must use an ISO-4217 three-letter code.
- Dates are normalized to ISO-8601.
- Invalid GSTIN values are quarantined rather than silently corrected.
- `amount` is always positive.
- Debit/credit direction is separate from business transaction type.
- Original source identifiers are retained for lineage.
- Record hashing excludes volatile ingestion metadata.
- Every normalized record receives an ingestion batch ID.
