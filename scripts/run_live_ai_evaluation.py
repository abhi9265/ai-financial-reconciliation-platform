"""Opt-in live-provider AI evaluation."""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from time import perf_counter

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.evaluation.adversarial import generate_adversarial_cases
from reconciliation_platform.reconciliation.advanced import reconcile_advanced
from reconciliation_platform.reconciliation.engine import ReconciliationDecision


def review_decisions(cases: int, seed: int) -> list[ReconciliationDecision]:
    decisions: list[ReconciliationDecision] = []
    for case in generate_adversarial_cases(seed=seed, cases=cases):
        for advanced in reconcile_advanced([case.bank], list(case.invoices)):
            if advanced.status != "REVIEW":
                continue
            decisions.append(
                ReconciliationDecision(
                    bank_record_id=advanced.bank_record_id,
                    counterparty_record_id=advanced.counterparty_record_ids[0]
                    if advanced.counterparty_record_ids else None,
                    status=advanced.status,
                    tier=advanced.tier,
                    confidence=advanced.confidence,
                    explanation=advanced.explanation,
                    signals=(),
                    amount_difference=advanced.amount_difference,
                    date_difference_days=advanced.date_difference_days,
                )
            )
    return decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="reports/live-ai-evaluation.json")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required; live evaluation is opt-in.")

    model = os.getenv("AI_MODEL", os.getenv("OPENAI_REVIEW_MODEL", "gpt-5.6-luna"))
    reviewer = OpenAIReviewer(
        api_key=api_key,
        model=model,
        timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
    )

    decisions = review_decisions(args.cases, args.seed)
    if not decisions:
        raise SystemExit("No deterministic REVIEW cases were generated.")

    recommendations = Counter()
    latencies_ms: list[float] = []
    errors = 0
    unsafe_auto_matches = 0

    for decision in decisions:
        started = perf_counter()
        try:
            result = reviewer.review(decision)
            recommendations[result.recommendation] += 1
            latency = (perf_counter() - started) * 1000
            latencies_ms.append(round(latency, 2))
            if result.recommendation == "MATCH" and not decision.counterparty_record_id:
                unsafe_auto_matches += 1
        except Exception:
            errors += 1

    successful = len(decisions) - errors
    report = {
        "provider": "openai",
        "model": model,
        "cases_requested": args.cases,
        "review_cases": len(decisions),
        "seed": args.seed,
        "recommendations": dict(recommendations),
        "provider_errors": errors,
        "success_rate": round(successful / len(decisions), 4),
        "unsafe_auto_match_recommendations": unsafe_auto_matches,
        "latency_ms": {
            "min": min(latencies_ms) if latencies_ms else None,
            "max": max(latencies_ms) if latencies_ms else None,
            "avg": round(sum(latencies_ms) / len(latencies_ms), 2) if latencies_ms else None,
        },
        "live_provider": True,
        "deterministic_engine_authoritative": True,
        "cost_note": "No hard-coded model pricing; calculate cost from provider pricing current at evaluation time.",
        "data_boundary": "Only bounded deterministic review evidence is sent to the provider.",
    }

    print(json.dumps(report, indent=2))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if errors or unsafe_auto_matches or successful == 0:
        raise SystemExit("Live AI evaluation failed reliability or safety gates.")


if __name__ == "__main__":
    main()
