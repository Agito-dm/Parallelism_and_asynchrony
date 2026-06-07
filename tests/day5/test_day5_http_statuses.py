import asyncio

import aiohttp

from crawler_day5.crawler import AsyncCrawler
from crawler_day5.retry_strategy import RetryStrategy


class FakeResponse:
    def __init__(self, status: int, text: str = "<html><body>OK</body></html>") -> None:
        self.status = status
        self._text = text

    async def text(self) -> str:
        return self._text


class FakeRequestContext:
    def __init__(
        self,
        response: FakeResponse | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response = response
        self.error = error

    async def __aenter__(self) -> FakeResponse:
        if self.error is not None:
            raise self.error

        assert self.response is not None
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class FakeSession:
    def __init__(self, responses_or_errors: list[FakeResponse | Exception]) -> None:
        self.responses_or_errors = responses_or_errors
        self.calls = 0
        self.requested_headers: list[dict | None] = []

    def get(self, url: str, headers: dict | None = None) -> FakeRequestContext:
        self.requested_headers.append(headers)

        item = self.responses_or_errors[min(self.calls, len(self.responses_or_errors) - 1)]
        self.calls += 1

        if isinstance(item, Exception):
            return FakeRequestContext(error=item)

        return FakeRequestContext(response=item)


async def test_day5_direct_fetch_url_retries_503_then_succeeds(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=2,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )
    fake_session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(200, "<html><body>Success</body></html>"),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/temporary")

    assert html == "<html><body>Success</body></html>"
    assert fake_session.calls == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 1
    assert stats["successful_retries"] == 1
    assert stats["failed_after_retries"] == 0


async def test_day5_direct_fetch_url_does_not_retry_404(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=3,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )
    fake_session = FakeSession(
        [
            FakeResponse(404),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/missing")

    assert html == ""
    assert fake_session.calls == 1

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["PermanentError"] == 1
    assert stats["successful_retries"] == 0
    assert stats["failed_after_retries"] == 0
    assert "https://example.com/missing" in stats["permanent_error_urls"]


async def test_day5_direct_fetch_url_retries_429_until_limit(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=2,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )
    fake_session = FakeSession(
        [
            FakeResponse(429),
            FakeResponse(429),
            FakeResponse(429),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/rate-limited")

    assert html == ""
    assert fake_session.calls == 3

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 3
    assert stats["failed_after_retries"] == 1
    assert stats["final_failures"] == 1


async def test_day5_direct_fetch_url_retries_timeout(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )
    fake_session = FakeSession(
        [
            asyncio.TimeoutError(),
            FakeResponse(200, "<html><body>After timeout</body></html>"),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/timeout")

    assert html == "<html><body>After timeout</body></html>"
    assert fake_session.calls == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 1
    assert stats["successful_retries"] == 1


async def test_day5_direct_fetch_url_retries_network_error(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )
    fake_session = FakeSession(
        [
            aiohttp.ClientError("network problem"),
            FakeResponse(200, "<html><body>After network error</body></html>"),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/network")

    assert html == "<html><body>After network error</body></html>"
    assert fake_session.calls == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["NetworkError"] == 1
    assert stats["successful_retries"] == 1
