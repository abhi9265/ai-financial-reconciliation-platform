import os\n\nfrom fastapi.testclient import TestClient

from reconciliation_platform.api.app import app

os.environ["RECONCILIATION_DB"] = ":memory:"\nclient = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reconcile_endpoint():
    response = client.post("/reconcile", json={"data_dir": "data/synthetic/seed"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] == 90
    assert body["review"] == 5
    assert body["unmatched"] == 5
    assert body["evaluation"]["precision"] == 1.0
    assert body["evaluation"]["recall"] == 1.0\n    assert body["review_cases_persisted"] == 5
