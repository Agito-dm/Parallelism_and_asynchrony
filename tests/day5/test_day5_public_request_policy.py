import asyncio

from crawler_day5.crawler import AsyncCrawler
from crawler_day5.retry_strategy import RetryStrategy


class FakeResponse:
    def __init__(
        self,
        status: int,
        text: str = "<html><head><title>OK</title></head><body>Hello</body></html>",
    ) -> None:
        self.status = status
        self._text = text

    async def text(self) -> str:
        return self._text


class FakeRequestContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class FakeSession:
    def __init__(self, responses_by_url: dict[str, list[FakeResponse]]) -> None:
        self.responses_by_url = responses_by_url
        self.calls_by_url: dict[str, int] = {}

    def get(self, url: str, headers: dict | None = None) -> FakeRequestContext:
        current_calls = self.calls_by_url.get(url, 0)
        self.calls_by_url[url] = current_calls + 1

        responses = self.responses_by_url[url]
        response = responses[min(current_calls, len(responses) - 1)]

        return FakeRequestContext(response)


async def test_day5_fetch_and_parse_uses_retry_strategy(monkeypatch):
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
    url = "https://example.com/temporary"

    fake_session = FakeSession(
        {
            url: [
                FakeResponse(503),
                FakeResponse(
                    200,
                    "<html><head><title>Recovered</title></head><body>Hello</body></html>",
                ),
            ],
        }
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    page_data = await crawler.fetch_and_parse(url)

    assert page_data["title"] == "Recovered"
    assert page_data["errors"] == []
    assert fake_session.calls_by_url[url] == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 1
    assert stats["successful_retries"] == 1


async def test_day5_fetch_urls_uses_retry_strategy_for_each_url(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=2,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )

    url_1 = "https://example.com/page-1"
    url_2 = "https://example.com/page-2"

    fake_session = FakeSession(
        {
            url_1: [
                FakeResponse(503),
                FakeResponse(200, "<html><body>Recovered page 1</body></html>"),
            ],
            url_2: [
                FakeResponse(200, "<html><body>Page 2</body></html>"),
            ],
        }
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    results = await crawler.fetch_urls([url_1, url_2])

    assert results[url_1] == "<html><body>Recovered page 1</body></html>"
    assert results[url_2] == "<html><body>Page 2</body></html>"

    assert fake_session.calls_by_url[url_1] == 2
    assert fake_session.calls_by_url[url_2] == 1

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 1
    assert stats["successful_retries"] == 1


async def test_day5_crawl_uses_retry_strategy(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=2,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )

    url = "https://example.com/start"

    fake_session = FakeSession(
        {
            url: [
                FakeResponse(503),
                FakeResponse(
                    200,
                    "<html><head><title>Crawl recovered</title></head><body>Hello</body></html>",
                ),
            ],
        }
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert url in crawler.processed_urls
    assert crawler.processed_urls[url]["title"] == "Crawl recovered"
    assert fake_session.calls_by_url[url] == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 1
    assert stats["successful_retries"] == 1


async def test_day5_crawl_records_permanent_error_without_retry(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=3,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )

    url = "https://example.com/missing"

    fake_session = FakeSession(
        {
            url: [
                FakeResponse(404),
            ],
        }
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert url not in crawler.processed_urls
    assert url in crawler.failed_urls
    assert url in crawler.permanent_error_urls
    assert fake_session.calls_by_url[url] == 1

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["PermanentError"] == 1
    assert stats["successful_retries"] == 0
    assert stats["failed_after_retries"] == 0
    assert url in stats["permanent_error_urls"]


async def test_day5_concurrent_fetch_url_calls_all_use_retry_policy(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=2,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )

    url_1 = "https://example.com/concurrent-1"
    url_2 = "https://example.com/concurrent-2"

    fake_session = FakeSession(
        {
            url_1: [
                FakeResponse(503),
                FakeResponse(200, "<html><body>Recovered 1</body></html>"),
            ],
            url_2: [
                FakeResponse(503),
                FakeResponse(200, "<html><body>Recovered 2</body></html>"),
            ],
        }
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    results = await asyncio.gather(
        crawler.fetch_url(url_1),
        crawler.fetch_url(url_2),
    )

    assert results == [
        "<html><body>Recovered 1</body></html>",
        "<html><body>Recovered 2</body></html>",
    ]

    assert fake_session.calls_by_url[url_1] == 2
    assert fake_session.calls_by_url[url_2] == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 2
    assert stats["successful_retries"] == 2
