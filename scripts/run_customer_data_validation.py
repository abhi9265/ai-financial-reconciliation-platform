"""Customer-shaped financial data validation suite."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from random import Random
from pydantic import ValidationError
from reconciliation_platform.models.canonical_transaction import (
    AmountDirection, CanonicalTransaction, SourceSystem, TransactionType,
    compute_record_hash,
)
from reconciliation_platform.reconciliation.advanced import reconcile_advanced

VENDORS = (
    "ACME Technologies Pvt Ltd", "Shree Ganesh Traders",
    "Mahindra Industrial Supplies", "BlueSky Logistics",
    "Narmada Office Solutions", "Aarav Packaging",
    "Tata Steel Distributors", "Gujarat Power Services",
)

def make_tx(source, rid, amount, day, name, tx_type, *, ref=None, invoice=None,
            file_name="bank.csv", row=1, description=None, gstin=None):
    amount = Decimal(str(amount))
    debit_types = {TransactionType.PAYMENT, TransactionType.PURCHASE}
    direction = AmountDirection.DEBIT if tx_type in debit_types else AmountDirection.CREDIT
    return CanonicalTransaction.from_business_fields(
        transaction_id=rid, source_system=source, source_record_id=rid,
        transaction_date=f"2026-08-{day:02d}",
        invoice_date=f"2026-08-{day:02d}" if invoice else None,
        transaction_type=tx_type, amount=amount, currency="INR",
        amount_direction=direction,
        debit=amount if direction == AmountDirection.DEBIT else None,
        credit=amount if direction == AmountDirection.CREDIT else None,
        description=description or name, reference_number=ref,
        invoice_number=invoice, counterparty_name=name,
        counterparty_gstin=gstin, source_file_name=file_name,
        source_row_number=row, source_schema_version="v1.0",
        ingestion_batch_id="customer-shaped-v1",
        ingested_at=datetime(2026, 8, 31, tzinfo=timezone.utc),
    )

def build_cases(seed=42, per_scenario=40):
    rng = Random(seed)
    cases = []
    for n in range(per_scenario):
        name = f"{VENDORS[n % len(VENDORS)].replace(' ', '')}{n:03d}"
        day = 1 + n % 20
        amount = Decimal(rng.randrange(5000, 50000)).quantize(Decimal("0.01"))
        base = f"CUST-{n:04d}"

        inv = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-EX-INV", amount, day, name,
                      TransactionType.PURCHASE, ref=f"INV-{n:05d}", invoice=f"INV-{n:05d}",
                      file_name="Tally_Purchase_Register.xlsx", row=n+2)
        bank = make_tx(SourceSystem.BANK, f"{base}-EX-BANK", amount, day+1, name,
                       TransactionType.PAYMENT, ref=f"INV-{n:05d}",
                       file_name="HDFC_Aug_2026.csv", row=n+2,
                       description=f"NEFT/{name}/INV-{n:05d}")
        cases.append(("exact_reference", bank, (inv,), "MATCHED", "ONE_TO_ONE", (inv.source_record_id,)))

        inv = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-FZ-INV", amount+Decimal("7.50"),
                      day, name, TransactionType.PURCHASE, ref=f"FZ-{n:05d}", invoice=f"FZ-{n:05d}",
                      file_name="Tally_Purchase_Register.xlsx", row=n+100)
        bank = make_tx(SourceSystem.BANK, f"{base}-FZ-BANK", amount, day, name,
                       TransactionType.PAYMENT, ref=f"FZ-{n:05d}",
                       file_name="ICICI_statement.csv", row=n+100,
                       description=f"IMPS {name} FZ-{n:05d}")
        cases.append(("amount_mismatch_review", bank, (inv,), "REVIEW", "AMBIGUOUS", (inv.source_record_id,)))

        a = (amount * Decimal(".40")).quantize(Decimal(".01"))
        b = amount - a
        i1 = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-P1", a, day, name,
                     TransactionType.PURCHASE, invoice=f"B-{n:05d}-1",
                     file_name="Tally_Purchase_Register.xlsx", row=n+200)
        i2 = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-P2", b, day, name,
                     TransactionType.PURCHASE, invoice=f"B-{n:05d}-2",
                     file_name="GST_Invoice_Export.xlsx", row=n+300)
        bank = make_tx(SourceSystem.BANK, f"{base}-P-BANK", amount, day+1, name,
                       TransactionType.PAYMENT, file_name="Axis_Bank_Aug.csv", row=n+200)
        cases.append(("one_to_many", bank, (i1, i2), "MATCHED", "ONE_TO_MANY",
                      tuple(sorted((i1.source_record_id, i2.source_record_id)))))

        inv = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-PP-INV", amount+Decimal("10000"),
                      day, name, TransactionType.PURCHASE, ref=f"PART-{n:05d}", invoice=f"PART-{n:05d}",
                      file_name="Tally_Purchase_Register.xlsx", row=n+400)
        bank = make_tx(SourceSystem.BANK, f"{base}-PP-BANK", amount, day+2, name,
                       TransactionType.PAYMENT, ref=f"PART-{n:05d}",
                       file_name="HDFC_Aug_2026.csv", row=n+400)
        cases.append(("partial_payment", bank, (inv,), "MATCHED", "PARTIAL_PAYMENT", (inv.source_record_id,)))

        inv = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-DT-INV", amount, day, name,
                      TransactionType.PURCHASE, ref=f"DATE-{n:05d}", invoice=f"DATE-{n:05d}",
                      file_name="Tally_Purchase_Register.xlsx", row=n+500)
        bank = make_tx(SourceSystem.BANK, f"{base}-DT-BANK", amount, day+7, name,
                       TransactionType.PAYMENT, ref=f"DATE-{n:05d}",
                       file_name="ICICI_statement.csv", row=n+500)
        cases.append(("date_window", bank, (inv,), "MATCHED", "ONE_TO_ONE", (inv.source_record_id,)))

        inv = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-UN-INV", amount+Decimal("50000"),
                      day, "Unrelated Counterparty", TransactionType.PURCHASE,
                      invoice=f"UN-{n:05d}", file_name="Tally_Purchase_Register.xlsx", row=n+600)
        bank = make_tx(SourceSystem.BANK, f"{base}-UN-BANK", amount, day,
                       "Unknown Customer", TransactionType.PAYMENT, ref=f"NO-{n:05d}",
                       file_name="HDFC_Aug_2026.csv", row=n+600)
        cases.append(("unmatched_exception", bank, (inv,), "UNMATCHED", "NONE", ()))

        fee = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-FEE", amount, day, name,
                      TransactionType.FEE, invoice=f"FEE-{n:05d}", file_name="Bank_Charges.csv", row=n+700)
        refund = make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-REF", amount, day, name,
                         TransactionType.REFUND, invoice=f"REF-{n:05d}", file_name="Credit_Notes.csv", row=n+800)
        bank = make_tx(SourceSystem.BANK, f"{base}-NOISE-BANK", amount, day, name,
                       TransactionType.PAYMENT, ref="NOT-A-PURCHASE",
                       file_name="Axis_Bank_Aug.csv", row=n+700)
        cases.append(("incompatible_noise", bank, (fee, refund), "UNMATCHED", "NONE", ()))

        x = (amount * Decimal(".25")).quantize(Decimal(".01"))
        y = (amount * Decimal(".35")).quantize(Decimal(".01"))
        z = amount - x - y
        invoices = tuple(
            make_tx(SourceSystem.PURCHASE_REGISTER, f"{base}-C{i}", v, day, name,
                    TransactionType.PURCHASE, invoice=f"C-{n:05d}-{i}",
                    file_name="Tally_Purchase_Register.xlsx", row=n+900+i)
            for i, v in enumerate((x, y, z), 1)
        )
        bank = make_tx(SourceSystem.BANK, f"{base}-C-BANK", amount, day+1, name,
                       TransactionType.PAYMENT, file_name="HDFC_Aug_2026.csv", row=n+900)
        cases.append(("three_way_complex", bank, invoices, "MATCHED", "ONE_TO_MANY",
                      tuple(sorted(i.source_record_id for i in invoices))))
    return cases

def validate_contract(sample):
    invalid = 0
    for currency, gstin in (("IN", None), ("INR", "BADGSTIN")):
        try:
            make_tx(SourceSystem.BANK, "INVALID", 100, 1, "Bad Row",
                    TransactionType.PAYMENT, currency=currency, gstin=gstin)
        except (ValidationError, ValueError):
            invalid += 1
    a = sample[1]
    b = a.model_copy(update={"source_file_name": "other.csv", "source_row_number": 999,
                             "ingestion_batch_id": "retry-batch"})
    return {
        "invalid_records_rejected": invalid,
        "record_hash_stable_across_ingestion_metadata": compute_record_hash(a) == compute_record_hash(b),
        "lineage_fields_present": bool(a.source_file_name and a.source_row_number and a.source_schema_version),
    }

def run(per_scenario=40, seed=42, output="customer-data-validation.json"):
    cases = build_cases(seed, per_scenario)
    decisions = reconcile_advanced([c[1] for c in cases], [i for c in cases for i in c[2]])
    failures = []
    scenario_counts = {}
    passed = 0
    for case, decision in zip(cases, decisions, strict=True):
        scenario, _, _, expected_status, expected_relationship, expected_ids = case
        scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
        ok = (decision.status == expected_status and decision.relationship == expected_relationship
              and set(decision.counterparty_record_ids) == set(expected_ids))
        passed += ok
        if not ok and len(failures) < 20:
            failures.append({"scenario": scenario, "bank_record_id": case[1].source_record_id,
                             "expected": [expected_status, expected_relationship, list(expected_ids)],
                             "actual": [decision.status, decision.relationship, list(decision.counterparty_record_ids)]})
    contract = validate_contract(cases[0])
    result = {
        "suite": "customer-shaped-financial-data-validation", "seed": seed, "cases": len(cases),
        "source_profiles": ["HDFC/ICICI/Axis-style bank CSVs", "Tally purchase register",
                            "GST invoice export", "bank charges and credit-note noise"],
        "scenario_counts": scenario_counts,
        "results": {"passed": passed, "failed": len(cases)-passed, "pass_rate": round(passed/len(cases), 6)},
        "canonical_contract": contract, "failure_samples": failures,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if output: Path(output).write_text(rendered + "\n", encoding="utf-8")
    if failures or contract["invalid_records_rejected"] != 2 or not contract["record_hash_stable_across_ingestion_metadata"] or not contract["lineage_fields_present"]:
        raise SystemExit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-scenario", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="customer-data-validation.json")
    args = parser.parse_args()
    run(args.per_scenario, args.seed, args.output)
