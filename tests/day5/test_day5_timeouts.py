import pytest

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
        self.timeouts = []

    def get(self, url: str, headers: dict | None = None, timeout=None) -> FakeRequestContext:
        self.timeouts.append(timeout)

        response = self.responses[min(self.calls, len(self.responses) - 1)]
        self.calls += 1

        return FakeRequestContext(response)


async def test_day5_total_timeout_increases_between_retries(monkeypatch):
    retry_strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    crawler = AsyncCrawler(
        max_concurrent=1,
        requests_per_second=1000.0,
        respect_robots=False,
        connect_timeout=0.5,
        read_timeout=0.75,
        total_timeout=1.0,
        timeout_backoff_factor=2.0,
        retry_strategy=retry_strategy,
    )

    fake_session = FakeSession(
        [
            FakeResponse(503),
            FakeResponse(200, "<html><body>Recovered</body></html>"),
        ]
    )

    async def fake_get_session() -> FakeSession:
        return fake_session

    monkeypatch.setattr(crawler, "_get_session", fake_get_session)

    html = await crawler.fetch_url("https://example.com/timeout-backoff")

    assert html == "<html><body>Recovered</body></html>"
    assert fake_session.calls == 2

    assert fake_session.timeouts[0].total == 1.0
    assert fake_session.timeouts[0].connect == 0.5
    assert fake_session.timeouts[0].sock_read == 0.75

    assert fake_session.timeouts[1].total == 2.0
    assert fake_session.timeouts[1].connect == 1.0
    assert fake_session.timeouts[1].sock_read == 1.5


def test_day5_crawler_rejects_invalid_timeout_settings():
    with pytest.raises(ValueError):
        AsyncCrawler(total_timeout=0)

    with pytest.raises(ValueError):
        AsyncCrawler(timeout_backoff_factor=0.5)
