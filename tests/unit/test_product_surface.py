from fastapi.routing import APIRoute

from reconciliation_platform.api.app import app


def test_dashboard_route_is_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert any(path == "/dashboard" for path in paths) or any(path.startswith("/dashboard") for path in paths)


def test_new_reconciliation_evidence_routes_are_registered():
    paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert "/v1/reconcile/jobs/{job_id}/results" in paths
    assert "/v1/reconcile/jobs/{job_id}/export.csv" in paths
    assert "/v1/reconcile/jobs/{job_id}/export.json" in paths
