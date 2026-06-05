from time import perf_counter

from crawler_day4.crawler import AsyncCrawler


class RecordingCrawler(AsyncCrawler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fetch_times: list[float] = []

    async def fetch_and_parse(self, url: str) -> dict:
        self.fetch_times.append(perf_counter())

        return {
            "url": url,
            "title": "",
            "metadata": {},
            "text": "",
            "links": [],
            "images": [],
            "headings": {},
            "tables": [],
            "lists": [],
            "errors": [],
        }


async def test_day4_crawler_respects_crawl_delay_from_robots(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=True,
        user_agent="MyBot/1.0",
    )

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow:
Crawl-delay: 0.05
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        [
            "https://example.com/page-1",
            "https://example.com/page-2",
        ],
        max_pages=2,
        show_progress=False,
    )

    assert len(crawler.fetch_times) == 2

    delay_between_fetches = crawler.fetch_times[1] - crawler.fetch_times[0]

    assert delay_between_fetches >= 0.045


async def test_day4_crawler_uses_user_agent_specific_crawl_delay(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=True,
        user_agent="MyBot/1.0",
    )

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow:
Crawl-delay: 0.01

User-agent: MyBot
Disallow:
Crawl-delay: 0.05
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        [
            "https://example.com/page-1",
            "https://example.com/page-2",
        ],
        max_pages=2,
        show_progress=False,
    )

    assert len(crawler.fetch_times) == 2

    delay_between_fetches = crawler.fetch_times[1] - crawler.fetch_times[0]

    assert delay_between_fetches >= 0.045


async def test_day4_crawler_does_not_apply_crawl_delay_when_robots_disabled(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
    )

    download_calls = 0

    async def fake_download_robots(robots_url: str) -> str:
        nonlocal download_calls
        download_calls += 1

        return """
User-agent: *
Crawl-delay: 10
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        [
            "https://example.com/page-1",
            "https://example.com/page-2",
        ],
        max_pages=2,
        show_progress=False,
    )

    assert download_calls == 0
    assert len(crawler.fetch_times) == 2
