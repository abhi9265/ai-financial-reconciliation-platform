from reconciliation_platform.api.app import app


def test_dashboard_route_is_registered():
    routes = {route.path for route in app.routes}
    assert "/dashboard" in routes


def test_new_reconciliation_evidence_routes_are_registered():
    routes = {route.path for route in app.routes}
    assert "/v1/reconcile/jobs/{job_id}/results" in routes
    assert "/v1/reconcile/jobs/{job_id}/export.csv" in routes
    assert "/v1/reconcile/jobs/{job_id}/export.json" in routes
