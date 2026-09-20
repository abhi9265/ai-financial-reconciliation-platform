import os

from fastapi.testclient import TestClient

from reconciliation_platform.api.app import app

os.environ["RECONCILIATION_DB"] = ":memory:"
os.environ["API_KEY_REQUIRED"] = "false"
client = TestClient(app)


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
    assert body["evaluation"]["recall"] == 1.0
    assert body["review_cases_persisted"] == 5


def test_protected_storage_requires_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("RECONCILIATION_API_KEY", "secret")
    response = client.get("/storage/health")
    assert response.status_code == 401

    response = client.get("/storage/health", headers={"X-API-Key": "secret"})
    assert response.status_code == 200



def test_tenant_reconcile_uploads_files(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", ":memory:")
    from pathlib import Path

    bank = Path("data/synthetic/seed/bank_transactions.csv").read_bytes()
    purchase = Path("data/synthetic/seed/purchase_invoices.csv").read_bytes()
    response = client.post(
        "/v1/reconcile",
        headers={"X-Tenant-ID": "acme_01"},
        files={
            "bank_file": ("bank.csv", bank, "text/csv"),
            "purchase_file": ("purchase.csv", purchase, "text/csv"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant_id"] == "acme_01"
    assert body["matched"] == 90
    assert body["review_cases_persisted"] == 5


def test_tenant_reconcile_requires_tenant(monkeypatch):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    response = client.post(
        "/v1/reconcile",
        files={
            "bank_file": ("bank.csv", b"a,b\\n1,2\\n", "text/csv"),
            "purchase_file": ("purchase.csv", b"a,b\\n1,2\\n", "text/csv"),
        },
    )
    assert response.status_code == 400
