from pathlib import Path

from reconciliation_platform.exports import report_json, results_csv
from reconciliation_platform.pipeline import run_pipeline, summarize
from reconciliation_platform.storage.sqlite import SQLiteStore


def test_upload_to_report_to_export_flow(tmp_path):
    source = Path("data/synthetic/seed")
    result = run_pipeline(source, tenant_id="e2e-tenant")
    report = summarize(result)
    store = SQLiteStore(tmp_path / "e2e.db")
    job_id = "e2e-job"
    assert store.save_reconciliation_results(
        job_id=job_id,
        tenant_id="e2e-tenant",
        decisions=result["decisions"],
    ) == len(result["decisions"])
    store.save_reconciliation_report(
        job_id=job_id,
        tenant_id="e2e-tenant",
        report=report,
    )
    stored = store.get_reconciliation_report(job_id, tenant_id="e2e-tenant")
    assert stored is not None
    rows, total = store.list_reconciliation_results(
        job_id=job_id,
        tenant_id="e2e-tenant",
        status="all",
        limit=500,
        offset=0,
    )
    assert total == len(result["decisions"])
    assert len(rows) == total
    assert "report_version" in stored["report"]
    assert "record_id" in results_csv(rows).splitlines()[0]
    assert report_json(stored["report"]).startswith("{")
    other_rows, other_total = store.list_reconciliation_results(
        job_id=job_id,
        tenant_id="other-tenant",
    )
    assert other_rows == []
    assert other_total == 0
