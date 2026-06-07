import pytest

from crawler_day4.crawler import AsyncCrawler as Day4AsyncCrawler
from crawler_day5.crawler import AsyncCrawler
from crawler_day5.errors import (
    CrawlerError,
    NetworkError,
    ParseError,
    PermanentError,
    TransientError,
)
from crawler_day5.retry_strategy import RetryStrategy


def test_day5_error_classes_are_available():
    assert issubclass(TransientError, CrawlerError)
    assert issubclass(PermanentError, CrawlerError)
    assert issubclass(NetworkError, CrawlerError)
    assert issubclass(ParseError, CrawlerError)


def test_day5_error_stores_context():
    original_error = RuntimeError("boom")

    error = TransientError(
        "temporary problem",
        url="https://example.com",
        status_code=503,
        original_error=original_error,
    )

    assert error.message == "temporary problem"
    assert error.url == "https://example.com"
    assert error.status_code == 503
    assert error.original_error is original_error
    assert "temporary problem" in str(error)
    assert "status_code=503" in str(error)


def test_day5_retry_strategy_can_be_created():
    strategy = RetryStrategy(
        max_retries=3,
        backoff_factor=2.0,
    )

    assert strategy.max_retries == 3
    assert strategy.backoff_factor == 2.0
    assert TransientError in strategy.retry_on
    assert NetworkError in strategy.retry_on


def test_day5_retry_strategy_rejects_invalid_values():
    with pytest.raises(ValueError):
        RetryStrategy(max_retries=-1)

    with pytest.raises(ValueError):
        RetryStrategy(backoff_factor=-1.0)


def test_day5_crawler_can_be_created():
    crawler = AsyncCrawler(
        max_concurrent=2,
        requests_per_second=5.0,
        respect_robots=True,
    )

    assert isinstance(crawler, AsyncCrawler)
    assert isinstance(crawler, Day4AsyncCrawler)
    assert isinstance(crawler.retry_strategy, RetryStrategy)


def test_day5_crawler_has_error_stats():
    crawler = AsyncCrawler()

    stats = crawler.get_error_stats()

    assert stats["successful_retries"] == 0
    assert stats["failed_after_retries"] == 0
    assert stats["average_retry_delay"] == 0.0
    assert stats["permanent_error_urls"] == []
    assert stats["total_error_events"] == 0
