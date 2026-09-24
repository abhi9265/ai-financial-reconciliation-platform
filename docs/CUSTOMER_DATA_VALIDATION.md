# Customer-Shaped Financial Data Validation

## Purpose

This suite bridges large synthetic scalability benchmarks and realistic financial-data behavior. It uses deterministic, intentionally messy transaction scenarios modeled on common Indian SME/accounting workflows without using customer data.

## Source profiles

- HDFC / ICICI / Axis-style bank statement CSVs
- Tally-style purchase registers
- GST-style invoice exports
- bank charges and credit-note/refund noise

These are representative workload shapes, not claims about any specific bank's private schema.

## Scenario coverage

| Scenario | Validation |
|---|---|
| Exact reference | Strong invoice/reference + amount agreement |
| Amount mismatch review | Reference exists but amount evidence is inconsistent |
| One-to-many | One payment settles multiple invoices |
| Partial payment | Payment allocation without prematurely consuming invoice balance |
| Date window | Settlement date within configured tolerance |
| Unmatched exception | No eligible counterparty remains unmatched |
| Incompatible noise | Fees/refunds are not treated as purchase matches |
| Three-way complex | Three invoices safely allocated to one payment |

The suite also validates malformed-record rejection, stable canonical hashing across ingestion metadata changes, and source lineage retention.

## CI gate

The customer-data-validation workflow runs the suite on relevant pull requests and uploads the machine-readable JSON result as an artifact.

## Scope

This is customer-shaped synthetic validation, not production customer data. It validates realistic data shapes and reconciliation contracts; source-specific adapters and customer acceptance datasets are still required for production rollout.
