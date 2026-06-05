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


async def test_day4_crawler_applies_rate_limiter_during_crawl():
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=20.0,
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


async def test_day4_crawler_respects_min_delay_between_requests():
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        min_delay=0.05,
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
    assert crawler.effective_requests_per_second == 20.0


async def test_day4_crawler_records_rate_statistics():
    crawler = RecordingCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=20.0,
    )

    await crawler.crawl(
        [
            "https://example.com/page-1",
            "https://example.com/page-2",
        ],
        max_pages=2,
        show_progress=False,
    )

    stats = crawler.get_rate_stats()

    assert stats["requests_per_second"] == 20.0
    assert stats["effective_requests_per_second"] == 20.0
    assert stats["total_requests"] == 2
    assert stats["blocked_by_robots"] == 0
    assert stats["current_requests_per_second"] >= 1
    assert stats["average_delay"] >= 0.0


async def test_day4_crawler_resets_rate_statistics_between_crawls():
    crawler = RecordingCrawler(
        max_concurrent=1,
        max_depth=0,
        requests_per_second=20.0,
    )

    await crawler.crawl(
        ["https://example.com/page-1"],
        max_pages=1,
        show_progress=False,
    )

    first_stats = crawler.get_rate_stats()

    assert first_stats["total_requests"] == 1

    await crawler.crawl(
        ["https://example.com/page-2"],
        max_pages=1,
        show_progress=False,
    )

    second_stats = crawler.get_rate_stats()

    assert second_stats["total_requests"] == 1
    assert list(crawler.processed_urls) == ["https://example.com/page-2"]
