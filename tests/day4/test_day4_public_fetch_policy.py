import asyncio
from time import perf_counter

from crawler_day4.crawler import AsyncCrawler


class FakeResponse:
    status = 200

    def raise_for_status(self) -> None:
        return None

    async def text(self) -> str:
        return "<html><body>Hello</body></html>"


class FakeRequestContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class FakeSession:
    def __init__(self) -> None:
        self.calls = 0
        self.request_times: list[float] = []
        self.requested_headers: list[dict | None] = []

    def get(self, url: str, headers: dict | None = None) -> FakeRequestContext:
        self.calls += 1
        self.request_times.append(perf_counter())
        self.requested_headers.append(headers)

        return FakeRequestContext(FakeResponse())


async def test_day4_direct_fetch_url_checks_robots_before_request(monkeypatch):
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=True,
    )
    fake_session = FakeSession()

    async def fake_get_session() -> FakeSession:
        return fake_session

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow: /private
"""

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)
    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    html = await crawler.fetch_url("https://example.com/private/page")

    assert html == ""
    assert fake_session.calls == 0
    assert "https://example.com/private/page" in crawler.blocked_urls

    stats = crawler.get_rate_stats()

    assert stats["blocked_by_robots"] == 1
    assert stats["total_requests"] == 0


async def test_day4_direct_fetch_url_applies_rate_limiter(monkeypatch):
    crawler = AsyncCrawler(
        max_concurrent=2,
        requests_per_second=20.0,
        respect_robots=False,
        max_retries=0,
    )
    fake_session = FakeSession()

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    await crawler.fetch_url("https://example.com/page-1")
    await crawler.fetch_url("https://example.com/page-2")

    assert fake_session.calls == 2

    delay_between_requests = (
        fake_session.request_times[1] - fake_session.request_times[0]
    )

    assert delay_between_requests >= 0.045

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 2


async def test_day4_direct_fetch_and_parse_checks_robots_before_request(monkeypatch):
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=True,
    )
    fake_session = FakeSession()

    async def fake_get_session() -> FakeSession:
        return fake_session

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow: /blocked
"""

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)
    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    page_data = await crawler.fetch_and_parse(
        "https://example.com/blocked/page"
    )

    assert fake_session.calls == 0
    assert "https://example.com/blocked/page" in crawler.blocked_urls
    assert "Failed to fetch HTML" in page_data["errors"]

    stats = crawler.get_rate_stats()

    assert stats["blocked_by_robots"] == 1
    assert stats["total_requests"] == 0


class SlowRawFetchCrawler(AsyncCrawler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.raw_fetch_times: list[float] = []

    async def _fetch_url_once(self, url: str) -> str:
        self.raw_fetch_times.append(perf_counter())
        await asyncio.sleep(0.05)

        return "<html><body>Hello</body></html>"


async def test_day4_concurrent_direct_fetch_url_calls_all_use_policy():
    crawler = SlowRawFetchCrawler(
        max_concurrent=2,
        requests_per_second=1000.0,
        respect_robots=False,
        max_retries=0,
    )

    results = await asyncio.gather(
        crawler.fetch_url("https://example.com/page-1"),
        crawler.fetch_url("https://example.com/page-2"),
    )

    assert results == [
        "<html><body>Hello</body></html>",
        "<html><body>Hello</body></html>",
    ]

    assert len(crawler.raw_fetch_times) == 2

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 2
