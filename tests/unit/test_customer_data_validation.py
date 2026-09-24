from scripts.run_customer_data_validation import build_cases, validate_contract
from reconciliation_platform.reconciliation.advanced import reconcile_advanced


def test_customer_shaped_suite_covers_expected_decisions():
    cases = build_cases(seed=42, per_scenario=40)
    decisions = reconcile_advanced(
        [case[1] for case in cases],
        [invoice for case in cases for invoice in case[2]],
    )
    assert len(cases) == 320
    for case, decision in zip(cases, decisions, strict=True):
        _, _, _, expected_status, expected_relationship, expected_ids = case
        assert decision.status == expected_status
        assert decision.relationship == expected_relationship
        assert set(decision.counterparty_record_ids) == set(expected_ids)


def test_customer_shaped_canonical_contract():
    contract = validate_contract(build_cases(seed=42, per_scenario=1)[0])
    assert contract["invalid_records_rejected"] == 2
    assert contract["record_hash_stable_across_ingestion_metadata"] is True
    assert contract["lineage_fields_present"] is True
