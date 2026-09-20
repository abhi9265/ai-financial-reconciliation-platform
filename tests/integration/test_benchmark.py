from reconciliation_platform.evaluation.metrics import evaluate_against_ground_truth, load_ground_truth
from reconciliation_platform.pipeline import run_pipeline


def test_synthetic_benchmark_regression() -> None:
    root = "data/synthetic/seed"
    result = run_pipeline(root)
    metrics = evaluate_against_ground_truth(
        result["decisions"],
        load_ground_truth(f"{root}/ground_truth.csv"),
    )

    assert metrics.actual_matches == 90
    assert metrics.actual_unmatched == 10
    assert metrics.correct_auto_matches == 90
    assert metrics.false_auto_matches == 0
    assert metrics.missed_matches == 0
    assert metrics.exception_capture_rate == 1.0
    assert metrics.pair_accuracy == 1.0
