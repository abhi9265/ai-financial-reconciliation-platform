"""Structured application logging helpers."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("reconciliation_platform")


def configure_logging(level: int = logging.INFO) -> None:
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)


def log_event(event: str, **fields: object) -> None:
    payload: dict[str, object] = {"event": event, **fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))


@contextmanager
def timed_event(event: str, fields: Mapping[str, object] | None = None) -> Iterator[None]:
    started = time.perf_counter()
    try:
        yield
    finally:
        log_event(event, duration_ms=round((time.perf_counter() - started) * 1000, 2), **dict(fields or {}))
