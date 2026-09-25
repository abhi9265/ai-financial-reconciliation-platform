# Phase 1 — Customer-Shaped Data Validation Report

## Status

**Complete and merged to `main`.**

Phase 1 adds a deterministic customer-shaped financial validation suite that sits between the existing large synthetic scalability benchmark and future staging/customer acceptance testing.

## What was validated

The suite generates **320 deterministic cases** using seed **42**: 40 cases for each of eight scenario families.

| Scenario | Cases | Expected behavior |
|---|---:|---|
| Exact reference | 40 | MATCHED / ONE_TO_ONE |
| Amount mismatch | 40 | REVIEW / AMBIGUOUS |
| One-to-many | 40 | MATCHED / ONE_TO_MANY |
| Partial payment | 40 | MATCHED / PARTIAL_PAYMENT |
| Date window | 40 | MATCHED / ONE_TO_ONE |
| Unmatched exception | 40 | UNMATCHED / NONE |
| Incompatible financial noise | 40 | UNMATCHED / NONE |
| Three-way complex | 40 | MATCHED / ONE_TO_MANY |
| **Total** | **320** | **Deterministic ground truth** |

## Source shapes represented

The workload intentionally models common Indian SME/accounting data shapes without using customer data:

- HDFC / ICICI / Axis-style bank statement CSVs
- Tally-style purchase-register exports
- GST-style invoice exports
- bank-charge records
- credit-note / refund records

These are representative shapes, **not claims about any bank's private schema**.

## Data-contract checks

The validation suite also checks:

- malformed record rejection
- INR/currency contract validation
- GSTIN validation
- source-file lineage
- source-row lineage
- schema-version retention
- canonical record-hash stability when ingestion metadata changes

The record hash is expected to remain stable when operational ingestion metadata changes, preserving deterministic business identity across retries/re-ingestion.

## CI gate

The suite is executed by:

`scripts/run_customer_data_validation.py --per-scenario 40 --seed 42`

and is enforced by:

`.github/workflows/customer-data-validation.yml`

The workflow:

1. installs the project and development dependencies
2. executes the deterministic suite
3. fails the build if any expected decision or contract assertion fails
4. uploads the machine-readable JSON result as a CI artifact

The implementation was merged through **PR #46** with merge commit:

`0251afffbcffafec416f3455c2688854bd4c1d3b`

## Engineering significance

This phase closes an important validation gap:

`large synthetic benchmark → customer-shaped scenarios → future staging/customer acceptance`

The test suite deliberately covers the kinds of ambiguity that are more representative of financial operations than a clean exact-match dataset: amount discrepancies, settlement windows, split payments, partial settlements, incompatible transactions and complex multi-invoice allocations.

## What this does NOT prove

This phase is **not** production customer validation.

It does not claim:

- real bank-schema compatibility
- production financial accuracy
- customer acceptance
- live cloud performance
- production SLA/SLO compliance
- production data privacy/compliance
- live AI-provider accuracy

Those require real source adapters, approved customer-shaped acceptance datasets, deployment infrastructure and operational validation.

## Exit criteria

| Criterion | Status |
|---|---|
| Deterministic customer-shaped scenarios | ✅ |
| Bank/Tally/GST-style source shapes | ✅ |
| Exact + fuzzy/ambiguous behavior | ✅ |
| One-to-many | ✅ |
| Partial payments | ✅ |
| Date-window behavior | ✅ |
| Unmatched exceptions | ✅ |
| Financial noise / incompatible types | ✅ |
| Complex three-way matching | ✅ |
| Canonical contract validation | ✅ |
| Hash stability / lineage checks | ✅ |
| Unit regression coverage | ✅ |
| CI gate | ✅ |
| Machine-readable evidence artifact | ✅ |
| Real customer data | ⏭️ Future |
| Production deployment | ⏭️ Phase 2 |
