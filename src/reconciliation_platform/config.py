"""Environment-backed runtime configuration."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    api_key: str | None
    database_path: str
    ai_provider: str
    ai_model: str
    ai_timeout_seconds: float
    api_key_required: bool

    @classmethod
    def from_env(cls) -> "Settings":
        provider = os.getenv("AI_PROVIDER", "none").strip().lower()
        return cls(
            api_key=os.getenv("RECONCILIATION_API_KEY"),
            database_path=os.getenv("RECONCILIATION_DB", "data/reconciliation.db"),
            ai_provider=provider,
            ai_model=os.getenv("AI_MODEL", "gpt-5.6-luna"),
            ai_timeout_seconds=float(os.getenv("AI_TIMEOUT_SECONDS", "20")),
            api_key_required=os.getenv("API_KEY_REQUIRED", "true").strip().lower() == "true",
        )
