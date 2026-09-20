from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from reconciliation_platform.api.app import app


ROOT = Path(__file__).parents[2]
BANK = ROOT / "data/synthetic/seed/bank_transactions.csv"
PURCHASE = ROOT / "data/synthetic/seed/purchase_invoices.csv"


def _headers() -> dict[str, str]:
    return {"X-API-Key": "root-key", "X-Tenant-ID": "acme_01"}


def test_sync_upload_is_tenant_bound_and_returns_benchmark_summary(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("RECONCILIATION_API_KEY", "root-key")
    monkeypatch.setenv("TENANT_API_KEYS", "acme_01:root-key")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "reconciliation.db"))
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("AI_PROVIDER", "none")

    client = TestClient(app)
    with BANK.open("rb") as bank, PURCHASE.open("rb") as purchase:
        response = client.post(
            "/v1/reconcile",
            headers=_headers(),
            files={
                "bank_file": ("bank.csv", bank, "text/csv"),
                "purchase_file": ("purchase.csv", purchase, "text/csv"),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tenant_id"] == "acme_01"
    assert payload["matched"] == 90
    assert payload["review"] == 5
    assert payload["unmatched"] == 5
    assert payload["ai_review"]["cases_reviewed"] == 5


def test_async_upload_creates_tenant_scoped_job(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("RECONCILIATION_API_KEY", "root-key")
    monkeypatch.setenv("TENANT_API_KEYS", "acme_01:root-key")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "reconciliation.db"))
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")
    monkeypatch.setenv("JOB_QUEUE", "background")
    monkeypatch.setenv("AI_PROVIDER", "none")

    client = TestClient(app)
    with BANK.open("rb") as bank, PURCHASE.open("rb") as purchase:
        response = client.post(
            "/v1/reconcile/async",
            headers=_headers(),
            files={
                "bank_file": ("bank.csv", bank, "text/csv"),
                "purchase_file": ("purchase.csv", purchase, "text/csv"),
            },
        )

    assert response.status_code == 202
    job = client.get(
        f"/v1/reconcile/jobs/{response.json()['job_id']}",
        headers=_headers(),
    )
    assert job.status_code == 200
    assert job.json()["tenant_id"] == "acme_01"
    assert job.json()["status"] == "succeeded"


def test_cross_tenant_job_access_is_rejected(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("API_KEY_REQUIRED", "true")
    monkeypatch.setenv("RECONCILIATION_API_KEY", "root-key")
    monkeypatch.setenv("TENANT_API_KEYS", "acme_01:acme-key,other_01:other-key")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "reconciliation.db"))
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    client = TestClient(app)
    assert client.get(
        "/v1/reconcile/jobs/not-your-job",
        headers={"X-API-Key": "acme-key", "X-Tenant-ID": "other_01"},
    ).status_code == 403
