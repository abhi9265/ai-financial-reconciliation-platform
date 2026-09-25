"""Structured application logging with request correlation."""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

logger = logging.getLogger("reconciliation_platform")
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def configure_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)


def set_request_id(request_id: str | None = None) -> str:
    value = request_id or uuid.uuid4().hex
    _request_id.set(value)
    return value


def get_request_id() -> str | None:
    return _request_id.get()


def log_event(event: str, **fields: object) -> None:
    payload: dict[str, object] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "event": event,
    }
    request_id = get_request_id()
    if request_id and "request_id" not in fields:
        payload["request_id"] = request_id
    payload.update(fields)
    logger.info(json.dumps(payload, default=str, sort_keys=True))


@contextmanager
def timed_event(event: str, fields: Mapping[str, object] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        log_event(
            event,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            outcome="error",
            error_type=type(exc).__name__,
            **dict(fields or {}),
        )
        raise
    else:
        log_event(
            event,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
            outcome="success",
            **dict(fields or {}),
        )
