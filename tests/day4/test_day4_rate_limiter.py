import asyncio
from time import perf_counter

import pytest

from crawler_day4.rate_limiter import RateLimiter


async def test_rate_limiter_waits_between_requests_for_same_domain():
    limiter = RateLimiter(requests_per_second=20.0, per_domain=True)

    started_at = perf_counter()

    await limiter.acquire("example.com")
    await limiter.acquire("example.com")

    elapsed = perf_counter() - started_at

    assert elapsed >= 0.045


async def test_rate_limiter_allows_different_domains_independently():
    limiter = RateLimiter(requests_per_second=1.0, per_domain=True)

    await limiter.acquire("example.com")

    await asyncio.wait_for(
        limiter.acquire("python.org"),
        timeout=0.2,
    )


async def test_rate_limiter_uses_global_limit_when_per_domain_is_false():
    limiter = RateLimiter(requests_per_second=1.0, per_domain=False)

    await limiter.acquire("example.com")

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            limiter.acquire("python.org"),
            timeout=0.2,
        )


async def test_rate_limiter_serializes_concurrent_requests_for_same_domain():
    limiter = RateLimiter(requests_per_second=20.0, per_domain=True)

    started_at = perf_counter()

    await asyncio.gather(
        limiter.acquire("example.com"),
        limiter.acquire("example.com"),
        limiter.acquire("example.com"),
    )

    elapsed = perf_counter() - started_at

    assert elapsed >= 0.09


async def test_rate_limiter_uses_default_key_when_domain_is_missing():
    limiter = RateLimiter(requests_per_second=20.0, per_domain=True)

    started_at = perf_counter()

    await limiter.acquire()
    await limiter.acquire()

    elapsed = perf_counter() - started_at

    assert elapsed >= 0.045
