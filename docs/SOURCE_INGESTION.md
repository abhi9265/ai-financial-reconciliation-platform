# Production-grade source ingestion

Phase 8 starts by separating **source parsing** from canonical normalization.

## Boundary

`uploaded bytes → source parser → validated source contract rows → canonical normalizer → reconciliation`

Parsers own source-format concerns such as:

- UTF-8 BOM handling
- source-specific column aliases
- CSV/JSON shape validation
- safe filename normalization
- clear format/contract errors

Normalization remains responsible for business semantics such as:

- dates and monetary values
- debit/credit direction
- transaction type
- canonical transaction IDs
- deterministic record hashes
- lineage and ingestion batch metadata

## Supported in the first slice

- Bank statement CSV
- Purchase register CSV
- Tally ledger CSV
- Tally ledger XLSX
- GST invoice JSON

The initial implementation now includes a dedicated Tally XLSX adapter with a bounded preamble/header scan. Arbitrary bank XLSX exports are intentionally not treated as supported until they have a source-specific contract and fixtures.

## Design rule

Do not add source-specific parsing branches to the reconciliation engine. New source formats should implement the parser boundary and produce the same contract-shaped rows.


## Phase 8 — Upload-to-Reconciliation Workflow

Phase 8 now has an upload-to-reconciliation execution path: validated bank and purchase uploads are parsed at the async job boundary, persisted as tenant-scoped raw objects, assigned deterministic batch fingerprints, and then executed by the existing reconciliation worker path. The job response exposes batch IDs and parsed row counts, and completed jobs expose a tenant-scoped report endpoint. Invalid source files fail before a reconciliation job is queued.


## Tenant-scoped batch lineage

Batch identity now includes the tenant scope for API-driven ingestion. The same source file fingerprint can therefore be registered independently for different tenants without sharing a batch identity. SQLite and PostgreSQL persistence store the tenant alongside each batch and enforce tenant-scoped uniqueness for source/fingerprint/schema combinations.

The reconciliation pipeline receives the tenant ID so the batch IDs reported after reconciliation match the IDs created at upload time. Local, non-tenant pipeline runs retain the `default` scope.
