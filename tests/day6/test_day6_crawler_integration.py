from crawler_day6.crawler import AsyncCrawler
from crawler_day6.storage import DataStorage


class MemoryStorage(DataStorage):
    def __init__(self) -> None:
        self.items = []
        self.closed = False

    async def save(self, data: dict) -> None:
        self.items.append(data)

    async def close(self) -> None:
        self.closed = True


class FakeResponse:
    def __init__(
        self,
        html: str,
        *,
        status: int = 200,
        headers: dict | None = None,
    ) -> None:
        self.html = html
        self.status = status
        self.headers = headers or {"Content-Type": "text/html"}

    async def text(self) -> str:
        return self.html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))

        return self.responses[url]


def make_crawler(storage=None, session=None):
    crawler = AsyncCrawler(
        storage=storage,
        respect_robots=False,
        requests_per_second=1000,
        max_concurrent=5,
    )

    if session is not None:
        async def fake_get_session():
            return session

        crawler._get_session = fake_get_session

    return crawler


async def test_day6_fetch_and_parse_saves_successful_page():
    storage = MemoryStorage()
    session = FakeSession(
        {
            "https://example.com": FakeResponse(
                """
                <html>
                    <head><title>Example page</title></head>
                    <body>
                        <p>Hello crawler</p>
                        <a href="https://example.com/about">About</a>
                    </body>
                </html>
                """
            )
        }
    )
    crawler = make_crawler(storage=storage, session=session)

    page_data = await crawler.fetch_and_parse("https://example.com")

    assert page_data is not None
    assert len(storage.items) == 1

    saved = storage.items[0]

    assert saved["url"] == "https://example.com"
    assert saved["title"] == "Example page"
    assert "Hello crawler" in saved["text"]
    assert "https://example.com/about" in saved["links"]
    assert saved["status_code"] == 200
    assert saved["content_type"] == "text/html"

    assert crawler.get_storage_stats() == {
        "saved": 1,
        "save_errors": 0,
        "failed_saves": 0,
    }

    await crawler.close()


async def test_day6_fetch_url_does_not_save_raw_html():
    storage = MemoryStorage()
    session = FakeSession(
        {
            "https://example.com": FakeResponse(
                "<html><head><title>Raw</title></head><body>Raw HTML</body></html>"
            )
        }
    )
    crawler = make_crawler(storage=storage, session=session)

    html = await crawler.fetch_url("https://example.com")

    assert "Raw HTML" in html
    assert storage.items == []
    assert crawler.get_storage_stats()["saved"] == 0

    await crawler.close()


async def test_day6_failed_page_is_not_saved():
    storage = MemoryStorage()
    session = FakeSession(
        {
            "https://example.com/missing": FakeResponse(
                "<html><body>Not found</body></html>",
                status=404,
            )
        }
    )
    crawler = make_crawler(storage=storage, session=session)

    page_data = await crawler.fetch_and_parse("https://example.com/missing")

    assert page_data is not None
    assert page_data.get("errors") == ["Failed to fetch HTML"]
    assert storage.items == []
    assert crawler.get_storage_stats()["saved"] == 0

    await crawler.close()


async def test_day6_crawl_saves_processed_pages():
    storage = MemoryStorage()
    session = FakeSession(
        {
            "https://example.com/1": FakeResponse(
                """
                <html>
                    <head><title>Page 1</title></head>
                    <body>First page</body>
                </html>
                """
            ),
            "https://example.com/2": FakeResponse(
                """
                <html>
                    <head><title>Page 2</title></head>
                    <body>Second page</body>
                </html>
                """
            ),
        }
    )
    crawler = make_crawler(storage=storage, session=session)

    await crawler.crawl(
        [
            "https://example.com/1",
            "https://example.com/2",
        ],
        max_pages=2,
    )

    assert len(storage.items) == 2

    saved_urls = sorted(item["url"] for item in storage.items)

    assert saved_urls == [
        "https://example.com/1",
        "https://example.com/2",
    ]

    assert crawler.get_storage_stats()["saved"] == 2

    await crawler.close()


async def test_day6_close_closes_storage():
    storage = MemoryStorage()
    crawler = make_crawler(storage=storage)

    await crawler.close()

    assert storage.closed is True
