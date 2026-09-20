import pytest

psycopg = pytest.importorskip("psycopg")

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
