"""Run measured scalability benchmarks for the adversarial reconciliation engine.

The high-volume scale gate deliberately uses a low complex-case mix. This
keeps the benchmark representative of a large reconciliation population while
the dedicated adversarial benchmark separately stress-tests one-to-many and
partial-payment search at a higher rate.
"""
from __future__ import annotations

import argparse
import json
import time
import tracemalloc

from reconciliation_platform.evaluation.adversarial import generate_adversarial_cases
from reconciliation_platform.reconciliation.advanced import reconcile_advanced


def run(
    cases_count: int,
    seed: int,
    one_to_many_rate: float,
    partial_rate: float,
) -> dict[str, object]:
    cases = generate_adversarial_cases(
        seed=seed,
        cases=cases_count,
        one_to_many_rate=one_to_many_rate,
        partial_rate=partial_rate,
    )
    bank = [case.bank for case in cases]
    invoices = [invoice for case in cases for invoice in case.invoices]

    tracemalloc.start()
    started = time.perf_counter()
    decisions = reconcile_advanced(bank, invoices)
    elapsed = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    expected_matches = sum(case.relationship == "MATCH" for case in cases)
    correct_matches = sum(
        case.relationship == "MATCH"
        and decision.status == "MATCHED"
        and set(decision.counterparty_record_ids) == set(case.expected_invoice_ids)
        for case, decision in zip(cases, decisions, strict=True)
    )
    review_expected = sum(case.relationship == "REVIEW" for case in cases)
    false_auto_matches = sum(
        case.relationship == "REVIEW" and decision.status == "MATCHED"
        for case, decision in zip(cases, decisions, strict=True)
    )
    partial_cases = sum(case.relationship == "PARTIAL" for case in cases)
    partial_correct = sum(
        case.relationship == "PARTIAL"
        and decision.relationship == "PARTIAL_PAYMENT"
        and decision.counterparty_record_ids == case.expected_invoice_ids
        for case, decision in zip(cases, decisions, strict=True)
    )
    candidate_pairs = sum(decision.candidate_count for decision in decisions)
    naive_pairs = len(bank) * len(invoices)

    return {
        "cases": cases_count,
        "bank_rows": len(bank),
        "invoice_rows": len(invoices),
        "seed": seed,
        "case_mix": {
            "one_to_many_rate": one_to_many_rate,
            "partial_rate": partial_rate,
            "review_rate": round(review_expected / cases_count, 6) if cases_count else 0.0,
        },
        "evaluation": {
            "full_match_recall": round(correct_matches / expected_matches, 6) if expected_matches else 0.0,
            "auto_match_precision": round(
                correct_matches / (correct_matches + false_auto_matches), 6
            )
            if correct_matches + false_auto_matches
            else 0.0,
            "partial_payment_accuracy": round(partial_correct / partial_cases, 6)
            if partial_cases
            else 0.0,
            "false_auto_matches": false_auto_matches,
            "expected_review_cases": review_expected,
        },
        "blocking": {
            "candidate_pairs": candidate_pairs,
            "naive_pairs": naive_pairs,
            "candidate_reduction_ratio": round(1 - candidate_pairs / naive_pairs, 6)
            if naive_pairs
            else 0.0,
        },
        "performance": {
            "elapsed_seconds": round(elapsed, 6),
            "bank_rows_per_second": round(len(bank) / elapsed, 2) if elapsed else 0.0,
            "peak_python_memory_mb": round(peak_bytes / (1024 * 1024), 3),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=int,
        nargs="+",
        default=[10_000, 100_000],
        help="One or more deterministic dataset sizes to benchmark.",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--one-to-many-rate",
        type=float,
        default=0.01,
        help="Fraction of high-volume cases using one-to-many matching.",
    )
    parser.add_argument(
        "--partial-rate",
        type=float,
        default=0.01,
        help="Fraction of high-volume cases using partial-payment matching.",
    )
    parser.add_argument("--output", type=str, default="")
    args = parser.parse_args()

    results = [
        run(size, args.seed, args.one_to_many_rate, args.partial_rate)
        for size in args.cases
    ]
    payload = {"benchmark": "adversarial-scale", "results": results}
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")


if __name__ == "__main__":
    main()
