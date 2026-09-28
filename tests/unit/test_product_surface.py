from fastapi.routing import APIRoute, Mount

from reconciliation_platform.api import app as app_module
from reconciliation_platform.api.app import app


def test_dashboard_route_is_registered():
    paths = {route.path for route in app.routes if isinstance(route, (APIRoute, Mount))}
    assert "/dashboard" in paths


def test_new_reconciliation_evidence_routes_are_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert "/v1/reconcile/jobs/{job_id}/results" in paths
    assert "/v1/reconcile/jobs/{job_id}/export.csv" in paths
    assert "/v1/reconcile/jobs/{job_id}/export.json" in paths


def test_reconciliation_result_endpoints(monkeypatch):
    class FakeStore:
        def get_job(self, job_id, *, tenant_id):
            return {"job_id": job_id, "tenant_id": tenant_id, "status": "succeeded"}
        def list_reconciliation_results(self, **kwargs):
            return ([{"record_id": "r1", "status": "MATCHED"}], 1)
        def get_reconciliation_report(self, job_id, *, tenant_id):
            return {"report": {"report_version": "1.0"}, "created_at": "now"}

    monkeypatch.setattr(app_module, "build_store", lambda settings: FakeStore())
    result = app_module.reconciliation_job_results("job-1", status="all", limit=100, offset=0, _=None, tenant_id="tenant-a")
    assert result["total"] == 1
    csv_response = app_module.export_reconciliation_csv("job-1", status="all", _=None, tenant_id="tenant-a")
    assert "record_id" in csv_response.body.decode()
    json_response = app_module.export_reconciliation_json("job-1", _=None, tenant_id="tenant-a")
    assert "report_version" in json_response.body.decode()


def test_bulk_review_decision_resolves_open_cases(monkeypatch):
    from reconciliation_platform.api import reviews as reviews_module

    class FakeStore:
        def __init__(self):
            self.cases = {
                "case-1": {"case_id": "case-1", "status": "open"},
                "case-2": {"case_id": "case-2", "status": "approved"},
            }
        def get_review_case(self, case_id, *, tenant_id):
            return self.cases.get(case_id)
        def resolve_review_case(self, case_id, *, tenant_id, status, note):
            if self.cases[case_id]["status"] != "open":
                return False
            self.cases[case_id]["status"] = status
            return True

    monkeypatch.setattr(reviews_module, "build_store", lambda settings: FakeStore())
    result = reviews_module.bulk_decide_reviews(
        reviews_module.BulkReviewDecisionRequest(
            case_ids=["case-1", "case-2", "missing"],
            action="approve",
            note="reviewed",
        ),
        _=None,
        tenant_id="tenant-a",
    )
    assert result["resolved"] == ["case-1"]
    assert {"case_id": "case-2", "reason": "already_resolved"} in result["conflicts"]
    assert {"case_id": "missing", "reason": "not_found"} in result["conflicts"]
