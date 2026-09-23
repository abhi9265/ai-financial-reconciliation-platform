"""Measured AI-review benchmark for 400 synthetic ambiguous cases.

The benchmark is intentionally opt-in because it requires a real OpenAI API
credential. It never treats an AI recommendation as an authoritative match.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from decimal import Decimal

from reconciliation_platform.ai.openai_reviewer import OpenAIReviewer
from reconciliation_platform.reconciliation.engine import ReconciliationConfig, reconcile
from reconciliation_platform.models.canonical_transaction import CanonicalTransaction, SourceSystem, TransactionType


def tx(record_id: str, amount: Decimal, day: int, name: str, *, bank: bool) -> CanonicalTransaction:
    return CanonicalTransaction.from_business_fields(
        transaction_id=record_id,
        source_system=SourceSystem.BANK if bank else SourceSystem.PURCHASE_REGISTER,
        source_record_id=record_id,
        transaction_date=f"2026-09-{day:02d}",
        invoice_date=None if bank else f"2026-09-{day:02d}",
        transaction_type=TransactionType.PAYMENT if bank else TransactionType.PURCHASE,
        amount=amount,
        currency="INR",
        description=name,
        reference_number=None,
        invoice_number=None if bank else record_id.replace("B", "I"),
        counterparty_name=name,
        ingestion_batch_id="ai-review-benchmark",
        ingested_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


def build_cases(count: int = 400) -> list[tuple[CanonicalTransaction, CanonicalTransaction, str]]:
    cases = []
    for n in range(count):
        amount = Decimal(10000 + n * 13)
        day = 1 + (n % 20)
        true_match = n % 2 == 0
        canonical = f"Vendor {n:04d}"
        variant = canonical.replace("Vendor", "VEND.").replace(" ", "  ")
        invoice_amount = amount if true_match else amount + Decimal("7.50")
        bank = tx(f"B{n:06d}", amount, min(day + 1, 28), canonical, bank=True)
        invoice = tx(f"I{n:06d}", invoice_amount, day, variant, bank=False)
        cases.append((bank, invoice, "MATCH" if true_match else "HUMAN_REVIEW"))
    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=400)
    parser.add_argument("--output", default="reports/ai-review-benchmark.json")
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for a live measured AI benchmark; no result was fabricated.")

    reviewer = OpenAIReviewer(api_key=api_key)
    config = ReconciliationConfig(
        fuzzy_review_threshold=0.40,
        fuzzy_auto_match_threshold=1.10,
    )
    cases = build_cases(args.cases)
    true_positive = 0
    false_positive = 0
    false_negative = 0
    abstentions = 0
    review_count = 0
    total_latency = 0.0
    rows = []

    for bank, invoice, expected in cases:
        decision = reconcile([bank], [invoice], config=config)[0]
        if decision.status != "REVIEW":
            raise RuntimeError(f"Benchmark contract violated for {bank.source_record_id}: {decision.status}")
        started = time.perf_counter()
        result = reviewer.review(decision)
        latency = time.perf_counter() - started
        total_latency += latency
        review_count += 1
        if expected == "MATCH" and result.recommendation == "MATCH":
            true_positive += 1
        elif expected == "MATCH" and result.recommendation != "MATCH":
            false_negative += 1
        elif expected == "HUMAN_REVIEW" and result.recommendation == "MATCH":
            false_positive += 1
        if result.recommendation == "HUMAN_REVIEW":
            abstentions += 1
        rows.append({
            "bank_record_id": bank.source_record_id,
            "expected": expected,
            "recommendation": result.recommendation,
            "confidence": result.confidence,
            "model": result.model,
            "latency_seconds": round(latency, 4),
        })

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    payload = {
        "benchmark": "ai-review-400",
        "cases": len(cases),
        "review_cases": review_count,
        "precision": round(true_positive / precision_denominator, 6) if precision_denominator else 0.0,
        "recall": round(true_positive / recall_denominator, 6) if recall_denominator else 0.0,
        "abstention_rate": round(abstentions / review_count, 6) if review_count else 0.0,
        "false_auto_matches": false_positive,
        "average_latency_seconds": round(total_latency / review_count, 4),
        "rows": rows,
    }
    path = args.output
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
