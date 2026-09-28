from pathlib import Path

from reconciliation_platform.pipeline import run_pipeline, summarize


def test_reconciliation_report_contains_lineage_and_evidence():
    result = run_pipeline(Path("data/synthetic/seed"))
    report = summarize(result)

    assert report["report_version"] == "1.0"
    assert report["bank_rows"] == 100
    assert report["purchase_rows"] == 95
    assert report["match_breakdown"]["by_status"] == {
        "matched": 90,
        "review": 5,
        "unmatched": 5,
    }
    assert report["source_batches"]["bank"]
    assert report["source_batches"]["purchase_register"]
    assert report["source_fingerprints"]["bank"]
    assert report["source_fingerprints"]["purchase_register"]
    assert len(report["anomaly_details"]) == report["anomalies"]
    assert len(report["quality_issue_details"]) == report["quality_issues"]
    assert all(
        item["amount_difference"] is None
        or isinstance(item["amount_difference"], str)
        for item in report["anomaly_details"]
    )
