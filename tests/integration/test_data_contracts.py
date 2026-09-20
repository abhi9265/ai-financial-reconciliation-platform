from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from reconciliation_platform.ingestion.contracts import SOURCE_CONTRACTS
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction


ROOT = Path(__file__).parents[2]


def test_source_contract_registry_matches_runtime_contracts() -> None:
    registry = json.loads((ROOT / "data/contracts/source_contracts.json").read_text())
    schema = json.loads((ROOT / "data/contracts/source_contracts.schema.json").read_text())
    Draft202012Validator(schema).validate(registry)

    assert set(registry["sources"]) == {source.value for source in SOURCE_CONTRACTS}
    for source, contract in SOURCE_CONTRACTS.items():
        assert set(registry["sources"][source.value]["required_columns"]) == set(contract.required_columns)
        assert set(registry["sources"][source.value]["optional_columns"]) == set(contract.optional_columns)


def test_canonical_transaction_contract_schema_is_valid() -> None:
    schema = json.loads((ROOT / "data/schemas/canonical_transaction.schema.json").read_text())
    Draft202012Validator.check_schema(schema)

    transaction = CanonicalTransaction.from_business_fields(
        transaction_id="contract-test-1",
        source_system="bank",
        source_record_id="contract-test-1",
        transaction_date="2026-01-01",
        transaction_type="PAYMENT",
        amount="100.00",
        currency="INR",
        amount_direction="DEBIT",
        debit="100.00",
        credit=None,
        ingestion_batch_id="batch-1",
        ingested_at="2026-01-01T00:00:00+00:00",
    )
    Draft202012Validator(schema).validate(json.loads(transaction.model_dump_json()))
