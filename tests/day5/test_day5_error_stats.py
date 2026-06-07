from crawler_day5.crawler import AsyncCrawler
from crawler_day5.retry_strategy import RetryStrategy


class FakeResponse:
    def __init__(self, status: int, text: str = "<html><body>OK</body></html>") -> None:
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
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = 0

    def get(self, url: str, headers: dict | None = None, timeout=None) -> FakeRequestContext:
        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1

        return FakeRequestContext(response)


async def test_day5_error_stats_include_retry_delay_and_final_failure(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.25,
    )

    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(retry_strategy, "_sleep", fake_sleep)

    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        retry_strategy=retry_strategy,
    )

    url = "https://example.com/always-503"

    fake_session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(503),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url(url)

    assert html == ""
    assert fake_session.calls == 2

    stats = crawler.get_error_stats()

    assert stats["errors_by_type"]["TransientError"] == 2
    assert stats["failed_after_retries"] == 1
    assert stats["average_retry_delay"] == 0.25
    assert stats["final_failures"] == 1

    report = crawler.get_error_report()

    assert report["error_stats"] == stats
    assert report["error_history"][0]["url"] == url
    assert report["retry_delays"] == [0.25]


async def test_day5_error_report_includes_permanent_errors(monkeypatch):
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

    url = "https://example.com/missing"

    fake_session = FakeSession(
        [
            FakeResponse(404),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url(url)

    assert html == ""
    assert fake_session.calls == 1

    report = crawler.get_error_report()

    assert url in report["permanent_errors"]
    assert report["error_history"][0]["url"] == url
    assert report["error_history"][0]["type"] == "PermanentError"
    assert report["error_history"][0]["status_code"] == 404
