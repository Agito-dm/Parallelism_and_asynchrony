from crawler_day4.crawler import AsyncCrawler


class RecordingCrawler(AsyncCrawler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fetched_urls: list[str] = []

    async def fetch_and_parse(self, url: str) -> dict:
        self.fetched_urls.append(url)

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


async def test_day4_crawler_blocks_url_disallowed_by_robots(monkeypatch):
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
Disallow: /private
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        ["https://example.com/private/page"],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetched_urls == []
    assert "https://example.com/private/page" in crawler.blocked_urls
    assert crawler.processed_urls == {}

    stats = crawler.get_rate_stats()

    assert stats["blocked_by_robots"] == 1
    assert stats["total_requests"] == 0


async def test_day4_crawler_fetches_url_allowed_by_robots(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=True,
    )

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: *
Disallow: /private
Allow: /public
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        ["https://example.com/public/page"],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetched_urls == ["https://example.com/public/page"]
    assert "https://example.com/public/page" in crawler.processed_urls
    assert crawler.blocked_urls == {}

    stats = crawler.get_rate_stats()

    assert stats["blocked_by_robots"] == 0
    assert stats["total_requests"] == 1


async def test_day4_crawler_ignores_robots_when_disabled(monkeypatch):
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
Disallow: /
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        ["https://example.com/private/page"],
        max_pages=1,
        show_progress=False,
    )

    assert download_calls == 0
    assert crawler.fetched_urls == ["https://example.com/private/page"]
    assert crawler.blocked_urls == {}


async def test_day4_crawler_uses_user_agent_for_robots_rules(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=True,
        user_agent="MyBot/1.0",
    )

    async def fake_download_robots(robots_url: str) -> str:
        return """
User-agent: MyBot
Disallow: /bot-blocked

User-agent: *
Disallow:
"""

    monkeypatch.setattr(
        crawler.robots_parser,
        "_download_robots",
        fake_download_robots,
    )

    await crawler.crawl(
        ["https://example.com/bot-blocked/page"],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetched_urls == []
    assert "https://example.com/bot-blocked/page" in crawler.blocked_urls


async def test_day4_crawler_reuses_robots_cache_for_same_domain(monkeypatch):
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=True,
    )

    download_calls = 0

    async def fake_download_robots(robots_url: str) -> str:
        nonlocal download_calls
        download_calls += 1

        return """
User-agent: *
Disallow:
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

    assert download_calls == 1
    assert set(crawler.fetched_urls) == {
        "https://example.com/page-1",
        "https://example.com/page-2",
    }
    assert crawler.blocked_urls == {}
