"""Tenant-scoped rate limiting with Redis-backed distributed enforcement."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from uuid import uuid4

from redis import Redis


class RateLimiter:
    """In-process fallback intended only for local development/tests."""

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
    """Atomic fixed-window limiter shared by all API replicas."""

    _SCRIPT = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then
      redis.call('EXPIRE', KEYS[1], ARGV[1])
    end
    return current
    """

    def __init__(self, redis_url: str, limit: int = 30, window_seconds: int = 60) -> None:
        self.client = Redis.from_url(redis_url, decode_responses=True)
        self.limit = limit
        self.window_seconds = window_seconds

    def allow(self, key: str) -> bool:
        bucket = int(time.time() // self.window_seconds)
        redis_key = f"reconciliation:ratelimit:{key}:{bucket}"
        current = self.client.eval(self._SCRIPT, 1, redis_key, self.window_seconds)
        return int(current) <= self.limit


def build_rate_limiter(settings) -> RateLimiter | RedisRateLimiter:
    """Build the configured limiter; Redis is the production default."""
    if settings.rate_limit_backend == "memory":
        return RateLimiter(settings.rate_limit_per_minute)
    return RedisRateLimiter(
        settings.redis_url,
        limit=settings.rate_limit_per_minute,
    )
