"""Run the synthetic reconciliation benchmark and emit machine-readable results."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.pipeline import run_pipeline, summarize


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/synthetic/seed")
    parser.add_argument("--output", default="benchmark-results.json")
    args = parser.parse_args()

    root = Path(args.data_dir)
    result = run_pipeline(root)
    metrics = evaluate_against_ground_truth(
        result["decisions"],
        load_ground_truth(root / "ground_truth.csv"),
    )
    payload = {
        "dataset": {
            "bank_rows": len(result["bank"]),
            "purchase_rows": len(result["purchase"]),
        },
        "summary": summarize(result),
        "evaluation": {
            "precision": metrics.match_precision,
            "recall": metrics.match_recall,
            "f1": metrics.match_f1,
            "false_positive_rate": metrics.false_positive_rate,
            "exception_capture_rate": metrics.exception_capture_rate,
            "pair_accuracy": metrics.pair_accuracy,
            "false_auto_matches": metrics.false_auto_matches,
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
