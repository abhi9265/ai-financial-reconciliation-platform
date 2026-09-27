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
