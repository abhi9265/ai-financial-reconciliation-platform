"""Run adversarial correctness and blocking benchmarks.

The benchmark reports measured results only; it never hard-codes expected
precision, recall, or performance claims.
"""
from __future__ import annotations

import argparse
import json
import time

from reconciliation_platform.evaluation.adversarial import generate_adversarial_cases
from reconciliation_platform.reconciliation.advanced import reconcile_advanced


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    cases = generate_adversarial_cases(seed=args.seed, cases=args.cases)
    bank = [c.bank for c in cases]
    invoices = [invoice for c in cases for invoice in c.invoices]

    started = time.perf_counter()
    decisions = reconcile_advanced(bank, invoices)
    elapsed = time.perf_counter() - started

    expected_matches = 0
    correct = 0
    false_auto = 0
    partial_correct = 0
    review_expected = 0
    for case, decision in zip(cases, decisions, strict=True):
        if case.relationship == "MATCH":
            expected_matches += 1
            if decision.status == "MATCHED" and set(decision.counterparty_record_ids) == set(case.expected_invoice_ids):
                correct += 1
        elif case.relationship == "PARTIAL":
            if decision.relationship == "PARTIAL_PAYMENT" and decision.counterparty_record_ids == case.expected_invoice_ids:
                partial_correct += 1
        elif case.relationship == "REVIEW":
            review_expected += 1
            if decision.status == "MATCHED":
                false_auto += 1

    auto_precision = correct / (correct + false_auto) if correct + false_auto else 0.0
    match_recall = correct / expected_matches if expected_matches else 0.0
    partial_accuracy = partial_correct / sum(c.relationship == "PARTIAL" for c in cases)
    candidate_pairs = sum(d.candidate_count for d in decisions)
    naive_pairs = len(bank) * len(invoices)
    payload = {
        "dataset": {
            "seed": args.seed,
            "bank_rows": len(bank),
            "invoice_rows": len(invoices),
            "cases": len(cases),
            "expected_one_to_many": sum(c.relationship == "MATCH" and len(c.expected_invoice_ids) > 1 for c in cases),
            "expected_partial": sum(c.relationship == "PARTIAL" for c in cases),
            "expected_review": review_expected,
        },
        "evaluation": {
            "auto_match_precision": auto_precision,
            "full_match_recall": match_recall,
            "partial_payment_accuracy": partial_accuracy,
            "false_auto_matches": false_auto,
        },
        "blocking": {
            "candidate_pairs": candidate_pairs,
            "naive_pairs": naive_pairs,
            "candidate_reduction_ratio": round(1 - (candidate_pairs / naive_pairs), 6) if naive_pairs else 0.0,
        },
        "performance": {
            "elapsed_seconds": round(elapsed, 6),
            "bank_rows_per_second": round(len(bank) / elapsed, 2) if elapsed else 0,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
