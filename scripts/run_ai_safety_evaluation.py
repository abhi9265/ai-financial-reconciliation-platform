"""Offline AI safety/evaluation harness for the advisory reviewer boundary.

No external model call is made. It validates that every deterministic REVIEW case
is passed through the provider contract and that unsafe MATCH recommendations are
downgraded when no deterministic candidate exists.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconciliation_platform.ai.reviewer import AIReviewResult, escalate_reviews
from reconciliation_platform.evaluation.adversarial import generate_adversarial_cases
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


class SyntheticReviewer:
    def review(self, decision: ReconciliationDecision) -> AIReviewResult:
        if decision.counterparty_record_id:
            return AIReviewResult("MATCH", 0.99, "Synthetic evaluator candidate exists.", "synthetic")
        return AIReviewResult("MATCH", 0.99, "Synthetic evaluator intentionally tests unsafe match.", "synthetic")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    cases = generate_adversarial_cases(seed=args.seed, cases=args.cases)
    decisions: list[ReconciliationDecision] = []
    for case in cases:
        from reconciliation_platform.reconciliation.advanced import reconcile_advanced
        decisions.extend(reconcile_advanced([case.bank], list(case.invoices)))

    review_count = sum(d.status == "REVIEW" for d in decisions)
    results = escalate_reviews(decisions, SyntheticReviewer())
    unsafe = sum(
        r.recommendation == "MATCH"
        and not next(d for d in decisions if d.bank_record_id == bank_id).counterparty_record_id
        for bank_id, r in results.items()
    )
    downgraded = sum(
        r.recommendation == "HUMAN_REVIEW"
        and "without a deterministic candidate" in r.rationale
        for r in results.values()
    )
    payload = {
        "cases": args.cases,
        "seed": args.seed,
        "review_cases": review_count,
        "provider_calls": len(results),
        "unsafe_auto_match_recommendations": unsafe,
        "unsafe_recommendations_downgraded": downgraded,
        "live_provider": False,
    }
    print(json.dumps(payload, indent=2))
    if unsafe or review_count != len(results):
        raise SystemExit("AI safety evaluation failed")
    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
