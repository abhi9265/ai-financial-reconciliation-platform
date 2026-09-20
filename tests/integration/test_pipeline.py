from pathlib import Path
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
