import pytest

from crawler_day3.crawler import AsyncCrawler


def test_day3_crawler_initial_state():
    crawler = AsyncCrawler(
        max_concurrent=5,
        max_depth=2,
        max_per_domain=2,
    )

    assert crawler.max_depth == 2
    assert crawler.visited_urls == set()
    assert crawler.failed_urls == {}
    assert crawler.processed_urls == {}


def test_day3_crawler_rejects_invalid_max_depth():
    with pytest.raises(ValueError):
        AsyncCrawler(max_depth=-1)


def test_day3_crawler_extracts_domain():
    crawler = AsyncCrawler()

    assert crawler._get_domain("https://Example.com/page") == "example.com"
    assert crawler._get_domain("http://127.0.0.1:8080/page") == "127.0.0.1:8080"


def test_day3_crawler_validates_urls():
    crawler = AsyncCrawler()

    assert crawler._is_valid_url("https://example.com/page") is True
    assert crawler._is_valid_url("http://example.com/page") is True

    assert crawler._is_valid_url("") is False
    assert crawler._is_valid_url("/relative/path") is False
    assert crawler._is_valid_url("mailto:test@example.com") is False
    assert crawler._is_valid_url("javascript:void(0)") is False
    assert crawler._is_valid_url("ftp://example.com/file") is False


def test_day3_crawler_gets_start_domains_from_valid_urls_only():
    crawler = AsyncCrawler()

    domains = crawler._get_start_domains(
        [
            "https://example.com",
            "https://docs.python.org/tutorial",
            "mailto:test@example.com",
            "/relative/path",
        ]
    )

    assert domains == {
        "example.com",
        "docs.python.org",
    }


def test_day3_crawler_filters_by_same_domain():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    assert crawler._should_crawl_url(
        url="https://example.com/about",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is True

    assert crawler._should_crawl_url(
        url="https://external.com/page",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is False


def test_day3_crawler_allows_external_domain_when_same_domain_disabled():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    assert crawler._should_crawl_url(
        url="https://external.com/page",
        start_domains=start_domains,
        same_domain_only=False,
        exclude_patterns=None,
        include_patterns=None,
    ) is True


def test_day3_crawler_filters_by_exclude_patterns():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    assert crawler._should_crawl_url(
        url="https://example.com/articles/page",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=[r"/admin", r"\.pdf$"],
        include_patterns=None,
    ) is True

    assert crawler._should_crawl_url(
        url="https://example.com/admin",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=[r"/admin", r"\.pdf$"],
        include_patterns=None,
    ) is False

    assert crawler._should_crawl_url(
        url="https://example.com/file.pdf",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=[r"/admin", r"\.pdf$"],
        include_patterns=None,
    ) is False


def test_day3_crawler_filters_by_include_patterns():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    assert crawler._should_crawl_url(
        url="https://example.com/docs/page",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=[r"/docs", r"/articles"],
    ) is True

    assert crawler._should_crawl_url(
        url="https://example.com/blog/page",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=[r"/docs", r"/articles"],
    ) is False


def test_day3_crawler_skips_already_known_urls():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    crawler.visited_urls.add("https://example.com/visited")
    crawler.processed_urls["https://example.com/processed"] = {}
    crawler.failed_urls["https://example.com/failed"] = "timeout"

    assert crawler._should_crawl_url(
        url="https://example.com/visited",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is False

    assert crawler._should_crawl_url(
        url="https://example.com/processed",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is False

    assert crawler._should_crawl_url(
        url="https://example.com/failed",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is False
