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


def test_tenant_api_key_is_bound_to_tenant(monkeypatch):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("TENANT_API_KEYS", "acme_01:key-acme,other_01:key-other")

    response = client.post(
        "/v1/reconcile",
        headers={"X-API-Key": "key-acme", "X-Tenant-ID": "other_01"},
        files={
            "bank_file": ("bank.csv", b"a,b\n1,2\n", "text/csv"),
            "purchase_file": ("purchase.csv", b"a,b\n1,2\n", "text/csv"),
        },
    )
    assert response.status_code == 403

    from pathlib import Path

    bank = Path("data/synthetic/seed/bank_transactions.csv").read_bytes()
    purchase = Path("data/synthetic/seed/purchase_invoices.csv").read_bytes()
    response = client.post(
        "/v1/reconcile",
        headers={"X-API-Key": "key-acme", "X-Tenant-ID": "acme_01"},
        files={
            "bank_file": ("bank.csv", bank, "text/csv"),
            "purchase_file": ("purchase.csv", purchase, "text/csv"),
        },
    )
    assert response.status_code == 200
    assert response.json()["tenant_id"] == "acme_01"


def test_async_reconciliation_job(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "jobs.db"))
    from pathlib import Path

    bank = Path("data/synthetic/seed/bank_transactions.csv").read_bytes()
    purchase = Path("data/synthetic/seed/purchase_invoices.csv").read_bytes()
    response = client.post(
        "/v1/reconcile/async",
        headers={"X-Tenant-ID": "async_01"},
        files={
            "bank_file": ("bank.csv", bank, "text/csv"),
            "purchase_file": ("purchase.csv", purchase, "text/csv"),
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    status = client.get(
        f"/v1/reconcile/jobs/{job_id}",
        headers={"X-Tenant-ID": "async_01"},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "succeeded"
    assert status.json()["result"]["matched"] == 90



def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "reconciliation_runs_total" in response.json()


def test_tenant_audit_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    from reconciliation_platform.audit import record_audit_event

    record_audit_event("test.event", tenant_id="audit_01", detail="ok")
    response = client.get("/v1/audit", headers={"X-Tenant-ID": "audit_01"})
    assert response.status_code == 200
    assert response.json()["events"][0]["event_type"] == "test.event"


def test_audit_is_tenant_scoped(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("AUDIT_LOG_PATH", str(tmp_path / "audit.jsonl"))
    from reconciliation_platform.audit import record_audit_event

    record_audit_event("test.event", tenant_id="tenant_a")
    record_audit_event("test.event", tenant_id="tenant_b")
    response = client.get("/v1/audit", headers={"X-Tenant-ID": "tenant_a"})
    assert [event["tenant_id"] for event in response.json()["events"]] == ["tenant_a"]


def test_rate_limiter_blocks_excess_requests():
    from reconciliation_platform.rate_limit import RateLimiter
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("tenant") is True
    assert limiter.allow("tenant") is False
    assert limiter.allow("other-tenant") is True


def test_async_reconciliation_idempotency_replays_existing_job(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "jobs.db"))
    from pathlib import Path
    bank = Path("data/synthetic/seed/bank_transactions.csv").read_bytes()
    purchase = Path("data/synthetic/seed/purchase_invoices.csv").read_bytes()
    headers = {"X-Tenant-ID": "idem_01", "Idempotency-Key": "same-request-001"}
    files = {"bank_file": ("bank.csv", bank, "text/csv"), "purchase_file": ("purchase.csv", purchase, "text/csv")}
    first = client.post("/v1/reconcile/async", headers=headers, files=files)
    second = client.post("/v1/reconcile/async", headers=headers, files=files)
    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["job_id"] == first.json()["job_id"]
    assert second.json()["idempotent_replay"] is True


def test_async_idempotency_is_tenant_scoped(monkeypatch, tmp_path):
    monkeypatch.setenv("API_KEY_REQUIRED", "false")
    monkeypatch.setenv("OBJECT_STORE", "local")
    monkeypatch.setenv("OBJECT_STORE_PATH", str(tmp_path / "objects"))
    monkeypatch.setenv("RECONCILIATION_DB", str(tmp_path / "jobs.db"))
    from pathlib import Path
    bank = Path("data/synthetic/seed/bank_transactions.csv").read_bytes()
    purchase = Path("data/synthetic/seed/purchase_invoices.csv").read_bytes()
    files = {"bank_file": ("bank.csv", bank, "text/csv"), "purchase_file": ("purchase.csv", purchase, "text/csv")}
    first = client.post("/v1/reconcile/async", headers={"X-Tenant-ID": "tenant_a", "Idempotency-Key": "shared-key"}, files=files)
    second = client.post("/v1/reconcile/async", headers={"X-Tenant-ID": "tenant_b", "Idempotency-Key": "shared-key"}, files=files)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["job_id"] != second.json()["job_id"]
