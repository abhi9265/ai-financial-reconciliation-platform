"""Append-only audit events for reconciliation operations."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()


def _audit_path() -> Path:
    return Path(os.getenv("AUDIT_LOG_PATH", "data/audit/events.jsonl"))


def record_audit_event(event_type: str, *, tenant_id: str | None = None, **details: Any) -> dict[str, Any]:
    event = {
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "tenant_id": tenant_id,
        **details,
    }
    path = _audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
    return event


def read_audit_events(*, tenant_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    if limit < 1:
        return []
    path = _audit_path()
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            event = json.loads(line)
            if tenant_id is None or event.get("tenant_id") == tenant_id:
                events.append(event)
    return events[-limit:]
