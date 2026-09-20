"""Environment-backed runtime configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    openai_api_key: str | None
    database_url: str | None
    database_path: str
    ai_provider: str
    ai_model: str
    ai_timeout_seconds: float
    api_key_required: bool
    object_store: str
    object_store_path: str
    s3_bucket: str | None
    s3_prefix: str

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("AI_PROVIDER", "none").strip().lower()
        return cls(
            api_key=os.getenv("RECONCILIATION_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            database_url=os.getenv("DATABASE_URL") or None,
            database_path=os.getenv("RECONCILIATION_DB", "data/reconciliation.db"),
            ai_provider=provider,
            ai_model=os.getenv("AI_MODEL", "gpt-5.6-luna"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
            api_key_required=os.getenv("API_KEY_REQUIRED", "true").strip().lower() == "true",
            object_store=os.getenv("OBJECT_STORE", "local").strip().lower(),
            object_store_path=os.getenv("OBJECT_STORE_PATH", "data/objects"),
            s3_bucket=os.getenv("S3_BUCKET") or None,
            s3_prefix=os.getenv("S3_PREFIX", "reconciliation"),
        )
