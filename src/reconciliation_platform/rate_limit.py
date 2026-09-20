"""Tenant-scoped rate limiting with Redis for distributed deployments."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Single-process fallback used when a shared limiter is unavailable."""

    def __init__(self, limit: int = 30, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True


class RedisRateLimiter:
    """Atomic fixed-window limiter suitable for multiple API replicas."""

    _SCRIPT = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then
        redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return current
    """

    def __init__(self, url: str, limit: int = 30, window_seconds: int = 60) -> None:
        from redis import Redis

        self.limit = limit
        self.window_seconds = window_seconds
        self._client = Redis.from_url(url, decode_responses=True)
        self._script = self._client.register_script(self._SCRIPT)

    def allow(self, key: str) -> bool:
        bucket = int(time.time() // self.window_seconds)
        redis_key = f"reconciliation:rate:{key}:{bucket}"
        current = int(self._script(keys=[redis_key], args=[self.window_seconds]))
        return current <= self.limit
