import asyncio
import logging
from time import perf_counter

import pytest
import pytest_asyncio
from aiohttp import web

from crawler_day1.crawler import AsyncCrawler


@pytest_asyncio.fixture
async def test_server(unused_tcp_port: int):
    async def ok_handler(_request):
        return web.Response(text="ok")

    async def slow_handler(_request):
        await asyncio.sleep(0.2)
        return web.Response(text="slow")

    async def error_handler(_request):
        return web.Response(status=500, text="server error")
    
    app = web.Application()
    app.router.add_get("/ok", ok_handler)
    app.router.add_get("/slow", slow_handler)
    app.router.add_get("/error", error_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    yield f"http://127.0.0.1:{unused_tcp_port}"

    await runner.cleanup()


@pytest.mark.asyncio
async def test_fetch_valid_url(test_server):
    async with AsyncCrawler(max_concurrent=2) as crawler:
        result = await crawler.fetch_url(f"{test_server}/ok")
    
    assert result == "ok"


@pytest.mark.asyncio
async def test_fetch_not_existing_url_returns_empty_string(test_server):
    async with AsyncCrawler(max_concurrent=2) as crawler:
        result = await crawler.fetch_url(f"{test_server}/not-found")

    assert result == ""


@pytest.mark.asyncio
async def test_fetch_server_error_returns_empty_string(test_server):
    async with AsyncCrawler(max_concurrent=2) as crawler:
        result = await crawler.fetch_url(f"{test_server}/error")

    assert result == ""


@pytest.mark.asyncio
async def test_timeout_returns_empty_string(test_server):
    async with AsyncCrawler(
        max_concurrent=2,
        connect_timeout=1.0,
        read_timeout=0.05,
    ) as crawler:
        result = await crawler.fetch_url(f"{test_server}/slow")

    assert result == ""


@pytest.mark.asyncio
async def test_fetch_urls_loads_multiple_urls(test_server):
    urls = [f"{test_server}/ok?id={index}" for index in range(5)]

    async with AsyncCrawler(max_concurrent=5) as crawler:
        results = await crawler.fetch_urls(urls)

    assert len(results) == 5
    assert set(results.keys()) == set(urls)
    assert all(page == "ok" for page in results.values())


@pytest.mark.asyncio
async def test_parallel_loading_is_faster_than_sequential(test_server):
    urls = [f"{test_server}/slow?id={index}" for index in range(5)]

    async with AsyncCrawler(max_concurrent=1) as crawler:
        start = perf_counter()

        for url in urls:
            await crawler.fetch_url(url)

        sequential_time = perf_counter() - start

    async with AsyncCrawler(max_concurrent=5) as crawler:
        start = perf_counter()
        await crawler.fetch_urls(urls)
        parallel_time = perf_counter() - start

    assert parallel_time < sequential_time


@pytest.mark.asyncio
async def test_logging_for_success_and_error(test_server, caplog):
    caplog.set_level(logging.INFO, logger="crawler_day1.crawler")

    async with AsyncCrawler(max_concurrent=2) as crawler:
        await crawler.fetch_url(f"{test_server}/ok")
        await crawler.fetch_url(f"{test_server}/not-found")

    messages = [record.getMessage() for record in caplog.records]

    assert any("Start loading URL" in message for message in messages)
    assert any("Successfully loaded URL" in message for message in messages)
    assert any("HTTP error while loading URL" in message for message in messages)


def test_max_concurrent_must_be_positive():
    with pytest.raises(ValueError):
        AsyncCrawler(max_concurrent=0)


@pytest.mark.asyncio
async def test_fetch_urls_handles_success_and_errors(test_server):
    urls = [
        f"{test_server}/ok",
        f"{test_server}/not-found",
        f"{test_server}/error",
    ]

    async with AsyncCrawler(max_concurrent=3) as crawler:
        results = await crawler.fetch_urls(urls)

    assert results[f"{test_server}/ok"] == "ok"
    assert results[f"{test_server}/not-found"] == ""
    assert results[f"{test_server}/error"] == ""
