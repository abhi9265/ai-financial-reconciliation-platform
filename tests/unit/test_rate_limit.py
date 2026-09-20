from reconciliation_platform.rate_limit import RateLimiter


def test_rate_limiter_isolated_by_key():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.allow("tenant-a") is True
    assert limiter.allow("tenant-a") is False
    assert limiter.allow("tenant-b") is True
