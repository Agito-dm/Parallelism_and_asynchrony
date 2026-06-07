import pytest

from crawler_day3.crawler_queue import CrawlerQueue


def test_crawler_queue_can_be_created():
    queue = CrawlerQueue()

    assert queue.get_stats() == {
        "queued": 0,
        "processed": 0,
        "failed": 0,
        "total_known": 0,
    }


@pytest.mark.asyncio
async def test_crawler_queue_returns_urls_by_priority():
    queue = CrawlerQueue()

    assert queue.add_url("https://example.com/low", priority=1) is True
    assert queue.add_url("https://example.com/high", priority=10) is True
    assert queue.add_url("https://example.com/medium", priority=5) is True

    assert await queue.get_next() == "https://example.com/high"
    assert await queue.get_next() == "https://example.com/medium"
    assert await queue.get_next() == "https://example.com/low"
    assert await queue.get_next() is None


@pytest.mark.asyncio
async def test_crawler_queue_keeps_fifo_order_for_same_priority():
    queue = CrawlerQueue()

    queue.add_url("https://example.com/first", priority=1)
    queue.add_url("https://example.com/second", priority=1)
    queue.add_url("https://example.com/third", priority=1)

    assert await queue.get_next() == "https://example.com/first"
    assert await queue.get_next() == "https://example.com/second"
    assert await queue.get_next() == "https://example.com/third"


def test_crawler_queue_rejects_duplicates_while_queued():
    queue = CrawlerQueue()

    assert queue.add_url("https://example.com/page") is True
    assert queue.add_url("https://example.com/page") is False

    assert queue.get_stats() == {
        "queued": 1,
        "processed": 0,
        "failed": 0,
        "total_known": 1,
    }


@pytest.mark.asyncio
async def test_crawler_queue_does_not_readd_processed_urls():
    queue = CrawlerQueue()

    queue.add_url("https://example.com/page")
    url = await queue.get_next()

    assert url == "https://example.com/page"

    queue.mark_processed(url)

    assert queue.add_url("https://example.com/page") is False
    assert queue.get_stats() == {
        "queued": 0,
        "processed": 1,
        "failed": 0,
        "total_known": 1,
    }


@pytest.mark.asyncio
async def test_crawler_queue_does_not_readd_failed_urls():
    queue = CrawlerQueue()

    queue.add_url("https://example.com/page")
    url = await queue.get_next()

    assert url == "https://example.com/page"

    queue.mark_failed(url, "timeout")

    assert queue.add_url("https://example.com/page") is False
    assert queue.get_stats() == {
        "queued": 0,
        "processed": 0,
        "failed": 1,
        "total_known": 1,
    }


@pytest.mark.asyncio
async def test_crawler_queue_stores_url_depth():
    queue = CrawlerQueue()

    queue.add_url("https://example.com", depth=0)
    queue.add_url("https://example.com/about", depth=1)

    assert queue.get_depth("https://example.com") == 0
    assert queue.get_depth("https://example.com/about") == 1
    assert queue.get_depth("https://example.com/unknown") == 0
