# Canonical Transaction Model

CanonicalTransaction is the executable Python representation of the canonical financial transaction contract.

The JSON Schema remains the interchange/documentation contract. The Pydantic model adds application-level invariants that JSON Schema alone does not express conveniently:

- debit/credit consistency with amount_direction
- tax-component arithmetic when all components are available
- deterministic SHA-256 record_hash validation
- rejection of unknown fields

Use CanonicalTransaction.from_business_fields(...) when creating a normalized record so the record hash is generated from the stable business payload.

The hash intentionally excludes transaction identity, source lineage, batch metadata, and ingestion timestamp. Those fields describe where/when a record was ingested rather than the underlying financial event.
