import logging

from crawler_day6.crawler import AsyncCrawler
from crawler_day6.storage import DataStorage


class FlakyStorage(DataStorage):
    def __init__(self) -> None:
        self.calls = 0
        self.items = []

    async def save(self, data: dict) -> None:
        self.calls += 1

        if self.calls == 1:
            raise OSError("Temporary write error")

        self.items.append(data)


class AlwaysFailingStorage(DataStorage):
    def __init__(self) -> None:
        self.calls = 0

    async def save(self, data: dict) -> None:
        self.calls += 1
        raise OSError("Disk is unavailable")


class FakeResponse:
    def __init__(self, html: str, *, status: int = 200) -> None:
        self.html = html
        self.status = status
        self.headers = {"Content-Type": "text/html"}

    async def text(self) -> str:
        return self.html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self) -> None:
        self.response = FakeResponse(
            """
            <html>
                <head><title>Error test</title></head>
                <body>Storage error test</body>
            </html>
            """
        )

    def get(self, url: str, **kwargs):
        return self.response


def make_crawler(storage):
    session = FakeSession()

    crawler = AsyncCrawler(
        storage=storage,
        storage_save_retries=2,
        storage_retry_delay=0,
        respect_robots=False,
        requests_per_second=1000,
    )

    async def fake_get_session():
        return session

    crawler._get_session = fake_get_session

    return crawler


async def test_day6_storage_save_is_retried_after_temporary_error():
    storage = FlakyStorage()
    crawler = make_crawler(storage)

    page_data = await crawler.fetch_and_parse("https://example.com")

    assert page_data is not None

    assert storage.calls == 2
    assert len(storage.items) == 1

    assert crawler.get_storage_stats() == {
        "saved": 1,
        "save_errors": 1,
        "failed_saves": 0,
    }

    await crawler.close()


async def test_day6_storage_save_failure_does_not_break_fetch_and_parse(caplog):
    storage = AlwaysFailingStorage()
    crawler = make_crawler(storage)

    caplog.set_level(logging.WARNING)

    page_data = await crawler.fetch_and_parse("https://example.com")

    assert page_data is not None

    assert storage.calls == 3

    assert crawler.get_storage_stats() == {
        "saved": 0,
        "save_errors": 3,
        "failed_saves": 1,
    }

    log_text = caplog.text

    assert "Storage save failed" in log_text
    assert "Storage save failed permanently" in log_text

    await crawler.close()
