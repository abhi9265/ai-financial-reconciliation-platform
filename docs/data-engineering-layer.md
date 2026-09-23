# Data Engineering Layer

The platform now exposes an explicit Bronze -> Silver -> Gold contract.

- Bronze: source rows preserved as received, partitioned by ingestion batch.
- Silver: canonical transactions validated against the executable Pydantic contract.
- Quarantine: invalid records are isolated with a row number and reason code instead of being dropped.
- Gold: reconciliation decisions become queryable Parquet outputs.
- Reprocessing: deterministic batch paths preserve lineage and make a failed batch replayable.

The implementation intentionally avoids adding an orchestration framework before the data contract and storage behavior are proven. Dagster/dbt can be layered on later when a real deployment requires scheduling or warehouse transformations.

This is a portfolio-grade local data-engineering contract; it is not a claim of a deployed cloud lakehouse.
