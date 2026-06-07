from crawler_day4.crawler import AsyncCrawler


def make_page(url: str, errors: list[str] | None = None) -> dict:
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
        "errors": errors or [],
    }


class FlakyCrawler(AsyncCrawler):
    def __init__(self, responses: list[dict], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.responses = responses
        self.fetch_count = 0

    async def fetch_and_parse(self, url: str) -> dict:
        response = self.responses[self.fetch_count]
        self.fetch_count += 1
        return response


async def test_day4_crawler_retries_after_failed_fetch():
    url = "https://example.com/page"

    crawler = FlakyCrawler(
        responses=[
            make_page(url, ["Failed to fetch HTML"]),
            make_page(url),
        ],
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        max_retries=1,
        backoff_base=0.001,
    )

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetch_count == 2
    assert url in crawler.processed_urls
    assert url not in crawler.failed_urls

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 2
    assert stats["backoff_count"] == 1


async def test_day4_crawler_marks_failed_after_max_retries():
    url = "https://example.com/page"

    crawler = FlakyCrawler(
        responses=[
            make_page(url, ["Failed to fetch HTML"]),
            make_page(url, ["Failed to fetch HTML"]),
            make_page(url, ["Failed to fetch HTML"]),
        ],
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        max_retries=2,
        backoff_base=0.001,
    )

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetch_count == 3
    assert url not in crawler.processed_urls
    assert url in crawler.failed_urls

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 3
    assert stats["backoff_count"] == 2


async def test_day4_crawler_retries_after_exception_then_succeeds():
    url = "https://example.com/page"

    class ExceptionThenSuccessCrawler(AsyncCrawler):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.fetch_count = 0

        async def fetch_and_parse(self, url: str) -> dict:
            self.fetch_count += 1

            if self.fetch_count == 1:
                raise RuntimeError("temporary error")

            return make_page(url)

    crawler = ExceptionThenSuccessCrawler(
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        max_retries=1,
        backoff_base=0.001,
    )

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetch_count == 2
    assert url in crawler.processed_urls
    assert url not in crawler.failed_urls

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 2
    assert stats["backoff_count"] == 1


async def test_day4_crawler_does_not_retry_when_max_retries_zero():
    url = "https://example.com/page"

    crawler = FlakyCrawler(
        responses=[
            make_page(url, ["Failed to fetch HTML"]),
        ],
        max_concurrent=1,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        max_retries=0,
        backoff_base=0.001,
    )

    await crawler.crawl(
        [url],
        max_pages=1,
        show_progress=False,
    )

    assert crawler.fetch_count == 1
    assert url in crawler.failed_urls

    stats = crawler.get_rate_stats()

    assert stats["total_requests"] == 1
    assert stats["backoff_count"] == 0
