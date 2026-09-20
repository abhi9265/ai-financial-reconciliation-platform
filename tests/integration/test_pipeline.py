from pathlib import Path

from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.pipeline import run_pipeline, summarize


def test_seed_pipeline_is_reproducible():
    result = run_pipeline(Path("data/synthetic/seed"))
    summary = summarize(result)
    assert summary["bank_rows"] == 100
    assert summary["purchase_rows"] == 95
    assert summary["matched"] == 90
    assert summary["review"] == 5
    assert summary["unmatched"] == 5
    assert summary["anomalies"] == 10


def test_seed_pipeline_meets_ground_truth_safety_contract():
    result = run_pipeline(Path("data/synthetic/seed"))
    truth = load_ground_truth(Path("data/synthetic/seed/ground_truth.csv"))
    metrics = evaluate_against_ground_truth(result["decisions"], truth)

    assert metrics.total == 100
    assert metrics.actual_matches == 90
    assert metrics.actual_unmatched == 10
    assert metrics.correct_auto_matches == 90
    assert metrics.false_auto_matches == 0
    assert metrics.missed_matches == 0
    assert metrics.match_precision == 1.0
    assert metrics.match_recall == 1.0
    assert metrics.pair_accuracy == 1.0
    assert metrics.exception_capture_rate == 1.0
