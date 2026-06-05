import pytest

from crawler_day4.crawler import AsyncCrawler
from crawler_day4.rate_limiter import RateLimiter
from crawler_day4.robots_parser import RobotsParser


def test_rate_limiter_can_be_created():
    limiter = RateLimiter(requests_per_second=2.0)

    assert limiter.requests_per_second == 2.0
    assert limiter.per_domain is True


def test_rate_limiter_rejects_invalid_speed():
    with pytest.raises(ValueError):
        RateLimiter(requests_per_second=0)

    with pytest.raises(ValueError):
        RateLimiter(requests_per_second=-1)


def test_robots_parser_default_allows_urls():
    parser = RobotsParser()

    assert parser.can_fetch("https://example.com/page") is True
    assert parser.get_crawl_delay() == 0.0


def test_day4_crawler_can_be_created():
    crawler = AsyncCrawler(
        max_concurrent=5,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.5,
        user_agent="MyBot/1.0",
    )

    assert crawler.max_concurrent == 5
    assert crawler.max_depth == 2
    assert crawler.respect_robots is True
    assert crawler.min_delay == 0.5
    assert crawler.user_agent == "MyBot/1.0"
    assert crawler.blocked_urls == {}


def test_day4_crawler_rejects_invalid_delays():
    with pytest.raises(ValueError):
        AsyncCrawler(min_delay=-0.1)

    with pytest.raises(ValueError):
        AsyncCrawler(jitter=-0.1)


def test_day4_crawler_has_rate_stats():
    crawler = AsyncCrawler(requests_per_second=2.0)
    stats = crawler.get_rate_stats()

    assert stats["requests_per_second"] == 2.0
    assert stats["average_delay"] == 0.0
    assert stats["blocked_by_robots"] == 0
    assert stats["total_requests"] == 0
