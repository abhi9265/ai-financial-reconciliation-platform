import pytest
from datetime import datetime, timezone

psycopg = pytest.importorskip("psycopg")

from reconciliation_platform.decisioning.review import ReviewCase  # noqa: E402
from reconciliation_platform.storage.postgres import PostgresStore  # noqa: E402


def test_postgres_store_requires_a_database_connection(monkeypatch):
    calls = []

    def fake_connect(url):
        calls.append(url)
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(psycopg, "connect", fake_connect)

    with pytest.raises(psycopg.OperationalError):
        PostgresStore("postgresql://invalid")

    assert calls == ["postgresql://invalid"]


def test_postgres_store_scopes_review_cases_by_tenant(monkeypatch):
    class FakeCursor:
        rowcount = 1

        def fetchall(self):
            return [("case_id",), ("tenant_id",)]

        def fetchone(self):
            return (2,)

    class FakeConnection:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.queries.append((query, params))
            return FakeCursor()

        def commit(self):
            pass

    connection = FakeConnection()
    monkeypatch.setattr(psycopg, "connect", lambda _: connection)

    store = PostgresStore("postgresql://test")
    case = ReviewCase(
        case_id="REVIEW-1",
        record_id="bank-1",
        candidate_record_id="invoice-1",
        reason="ambiguous",
        confidence=0.71,
        created_at=datetime.now(timezone.utc),
    )

    assert store.save_review_cases([case], tenant_id="acme_01") == 1
    assert store.review_case_count(tenant_id="acme_01") == 2

    insert = next(item for item in connection.queries if "INSERT INTO review_cases" in item[0])
    assert insert[1][0] == "acme_01:REVIEW-1"
    assert insert[1][1] == "acme_01"
