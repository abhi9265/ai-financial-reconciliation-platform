from reconciliation_platform.rate_limit import RateLimiter, RedisRateLimiter


class FakeRedis:
    def __init__(self):
        self.calls = []

    def eval(self, script, keys, redis_key, window):
        self.calls.append((script, keys, redis_key, window))
        return 1


def test_memory_rate_limiter_enforces_window_limit() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.allow("tenant") is True
    assert limiter.allow("tenant") is True
    assert limiter.allow("tenant") is False


def test_redis_rate_limiter_uses_atomic_counter() -> None:
    limiter = RedisRateLimiter("redis://unused", limit=2)
    limiter.client = FakeRedis()
    assert limiter.allow("tenant") is True
    assert limiter.client.calls[0][1] == 1
    assert "reconciliation:ratelimit:tenant:" in limiter.client.calls[0][2]
