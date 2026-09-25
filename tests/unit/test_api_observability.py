from fastapi.testclient import TestClient

from reconciliation_platform.api.app import app


def test_metrics_endpoint_exposes_prometheus_format():
    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "reconciliation_http_requests_total" in response.text
    assert response.headers["content-type"].startswith("text/plain")


def test_health_is_liveness_check():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
