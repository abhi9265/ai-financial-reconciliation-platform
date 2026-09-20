"""Persistence backend selection."""
from __future__ import annotations

from reconciliation_platform.config import Settings
from reconciliation_platform.storage.postgres import PostgresStore
from reconciliation_platform.storage.sqlite import SQLiteStore


def build_store(settings: Settings):
    if settings.database_url:
        return PostgresStore(settings.database_url)
    return SQLiteStore(settings.database_path)
