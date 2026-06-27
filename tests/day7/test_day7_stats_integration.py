from crawler_day7.crawler import AdvancedCrawler


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

    def get(self, url: str, **kwargs):
        return self.responses[url]


def make_crawler(session: FakeSession) -> AdvancedCrawler:
    crawler = AdvancedCrawler(
        respect_robots=False,
        requests_per_second=1000,
        max_concurrent=5,
    )

    async def fake_get_session():
        return session

    crawler._get_session = fake_get_session

    return crawler


async def test_day7_fetch_and_parse_records_success_stats():
    url = "https://example.com/created"

    session = FakeSession(
        {
            url: FakeResponse(
                """
                <html>
                    <head><title>Created</title></head>
                    <body>Created page</body>
                </html>
                """,
                status=201,
                headers={"Content-Type": "application/xhtml+xml"},
            )
        }
    )
    crawler = make_crawler(session)

    page_data = await crawler.fetch_and_parse(url)

    assert page_data is not None

    stats = crawler.get_stats()

    assert stats["total_pages"] == 1
    assert stats["successful"] == 1
    assert stats["failed"] == 0
    assert stats["status_codes"] == {"201": 1}
    assert stats["top_domains"] == {"example.com": 1}
    assert stats["started_at"] is not None
    assert stats["duration_seconds"] >= 0

    await crawler.close()


async def test_day7_fetch_and_parse_records_failed_stats():
    url = "https://example.com/missing"

    session = FakeSession(
        {
            url: FakeResponse(
                "<html><body>Not found</body></html>",
                status=404,
            )
        }
    )
    crawler = make_crawler(session)

    page_data = await crawler.fetch_and_parse(url)

    assert page_data is not None

    stats = crawler.get_stats()

    assert stats["total_pages"] == 1
    assert stats["successful"] == 0
    assert stats["failed"] == 1
    assert stats["top_domains"] == {"example.com": 1}

    await crawler.close()


async def test_day7_crawl_records_started_and_finished_time():
    url_1 = "https://example.com/page-1"
    url_2 = "https://example.com/page-2"

    session = FakeSession(
        {
            url_1: FakeResponse(
                """
                <html>
                    <head><title>Page 1</title></head>
                    <body>First page</body>
                </html>
                """
            ),
            url_2: FakeResponse(
                """
                <html>
                    <head><title>Page 2</title></head>
                    <body>Second page</body>
                </html>
                """
            ),
        }
    )
    crawler = make_crawler(session)

    await crawler.crawl(
        [url_1, url_2],
        max_pages=2,
        show_progress=False,
    )

    stats = crawler.get_stats()

    assert stats["total_pages"] == 2
    assert stats["successful"] == 2
    assert stats["failed"] == 0
    assert stats["status_codes"] == {"200": 2}
    assert stats["top_domains"] == {"example.com": 2}
    assert stats["started_at"] is not None
    assert stats["finished_at"] is not None
    assert stats["duration_seconds"] >= 0
    assert stats["pages_per_second"] >= 0

    await crawler.close()
