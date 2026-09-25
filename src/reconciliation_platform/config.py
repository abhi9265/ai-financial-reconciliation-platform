"""Environment-backed runtime configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote


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
    tenant_api_keys: dict[str, str]
    job_queue: str
    redis_url: str
    rate_limit_per_minute: int
    rate_limit_backend: str

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("AI_PROVIDER", "none").strip().lower()
        raw_tenants = os.getenv("TENANT_API_KEYS", "")
        tenant_api_keys: dict[str, str] = {}
        for entry in raw_tenants.split(","):
            if not entry.strip() or ":" not in entry:
                continue
            tenant, key = entry.split(":", 1)
            if tenant.strip() and key.strip():
                tenant_api_keys[key.strip()] = tenant.strip()

        database_url = os.getenv("DATABASE_URL") or None
        if not database_url and os.getenv("DATABASE_HOST"):
            database_user = os.getenv("DATABASE_USER", "reconciliation")
            database_password = os.getenv("DATABASE_PASSWORD", "")
            database_name = os.getenv("DATABASE_NAME", "reconciliation")
            database_port = os.getenv("DATABASE_PORT", "5432")
            database_url = (
                f"postgresql://{quote(database_user, safe='')}:{quote(database_password, safe='')}"
                f"@{os.environ['DATABASE_HOST']}:{database_port}/{quote(database_name, safe='')}"
            )

        return cls(
            api_key=os.getenv("RECONCILIATION_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            database_url=database_url,
            database_path=os.getenv("RECONCILIATION_DB", "data/reconciliation.db"),
            ai_provider=provider,
            ai_model=os.getenv("AI_MODEL", "gpt-5.6-luna"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
            api_key_required=os.getenv("API_KEY_REQUIRED", "true").strip().lower() == "true",
            object_store=os.getenv("OBJECT_STORE", "local").strip().lower(),
            object_store_path=os.getenv("OBJECT_STORE_PATH", "data/objects"),
            s3_bucket=os.getenv("S3_BUCKET") or None,
            s3_prefix=os.getenv("S3_PREFIX", "reconciliation"),
            tenant_api_keys=tenant_api_keys,
            job_queue=os.getenv("JOB_QUEUE", "background").strip().lower(),
            redis_url=os.getenv("REDIS_URL", "redis://redis:6379/0"),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "30")),
            rate_limit_backend=os.getenv("RATE_LIMIT_BACKEND", "memory").strip().lower(),
        )
