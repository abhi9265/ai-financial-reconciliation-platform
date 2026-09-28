from reconciliation_platform.exports import report_json, results_csv
from reconciliation_platform.storage.sqlite import SQLiteStore


def test_results_are_persisted_and_exportable(tmp_path):
    store = SQLiteStore(tmp_path / "results.db")
    job_id = "job-1"
    tenant_id = "tenant-a"
    class Decision:
        bank_record_id = "bank-1"
        counterparty_record_id = "invoice-1"
        status = "MATCHED"
        tier = "EXACT"
        confidence = 1.0
        explanation = "Reference and amount matched."
        amount_difference = None
    assert store.save_reconciliation_results(job_id=job_id, tenant_id=tenant_id, decisions=[Decision()]) == 1
    rows, total = store.list_reconciliation_results(job_id=job_id, tenant_id=tenant_id)
    assert total == 1
    assert rows[0]["status"] == "MATCHED"
    csv_text = results_csv(rows)
    assert "bank-1" in csv_text
    assert "MATCHED" in csv_text
    assert '"status"' not in csv_text
    assert '"matched"' in report_json({"matched": 1})


def test_result_listing_is_tenant_isolated(tmp_path):
    store = SQLiteStore(tmp_path / "results.db")
    class Decision:
        bank_record_id = "bank-1"
        counterparty_record_id = None
        status = "UNMATCHED"
        tier = "NONE"
        confidence = 0.0
        explanation = "No candidate."
        amount_difference = None
    store.save_reconciliation_results(job_id="job-1", tenant_id="tenant-a", decisions=[Decision()])
    rows, total = store.list_reconciliation_results(job_id="job-1", tenant_id="tenant-b")
    assert rows == []
    assert total == 0
