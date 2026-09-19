# Source-to-Canonical Mapping

Source-specific schemas terminate at ingestion. Downstream reconciliation consumes canonical records.

## Bank statement

| Source | Canonical |
|---|---|
| transaction_id | source_record_id |
| transaction_date | transaction_date |
| value_date | value_date |
| debit | debit |
| credit | credit |
| amount | amount |
| narration | description |
| reference | reference_number |
| account_number | bank_account |

## Purchase / sales register

| Source | Canonical |
|---|---|
| document_id | source_record_id |
| invoice_date | invoice_date / transaction_date |
| invoice_number | invoice_number |
| vendor_name / customer_name | vendor_name |
| gstin | vendor_gstin |
| taxable_value | taxable_amount |
| cgst / sgst / igst | corresponding tax fields |
| total | amount |
| document_type | transaction_type |

## Tally

Preserve the original voucher/ledger identifier as source_record_id and map common business fields to the canonical model.

## GST

Use GST records as tax and invoice reference evidence, not as the sole source of truth.

## Invariants

- Amounts are represented in INR.
- Dates are normalized to ISO-8601.
- Invalid GSTIN values are quarantined rather than silently corrected.
- Original source identifiers are retained for lineage.
- Every normalized record receives an ingestion batch ID and deterministic record hash.
