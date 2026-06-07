import pytest
import pytest_asyncio
from aiohttp import web

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


@pytest_asyncio.fixture
async def day3_test_server(unused_tcp_port: int):
    async def root_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>Root Page</title>
            </head>
            <body>
                <h1>Root</h1>
                <a href="/page1">Page 1</a>
                <a href="/page2">Page 2</a>
                <a href="/page1">Duplicate Page 1</a>
                <a href="https://external.com/page">External</a>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    async def page1_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>Page 1</title>
            </head>
            <body>
                <h1>Page 1</h1>
                <a href="/deep">Deep Page</a>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    async def page2_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>Page 2</title>
            </head>
            <body>
                <h1>Page 2</h1>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    async def deep_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>Deep Page</title>
            </head>
            <body>
                <h1>Deep</h1>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    async def with_missing_handler(_request):
        return web.Response(
            text="""
            <html>
            <head>
                <title>With Missing</title>
            </head>
            <body>
                <h1>With Missing</h1>
                <a href="/missing">Missing Page</a>
            </body>
            </html>
            """,
            content_type="text/html",
        )

    app = web.Application()
    app.router.add_get("/", root_handler)
    app.router.add_get("/page1", page1_handler)
    app.router.add_get("/page2", page2_handler)
    app.router.add_get("/deep", deep_handler)
    app.router.add_get("/with-missing", with_missing_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()

    yield f"http://127.0.0.1:{unused_tcp_port}"

    await runner.cleanup()


@pytest.mark.asyncio
async def test_day3_crawl_processes_start_page_only_when_max_depth_zero(
    day3_test_server,
):
    start_url = f"{day3_test_server}/"

    async with AsyncCrawler(max_concurrent=3, max_depth=0) as crawler:
        results = await crawler.crawl(
            start_urls=[start_url],
            max_pages=10,
            same_domain_only=True,
            show_progress=False,
        )

    assert set(results.keys()) == {start_url}
    assert crawler.visited_urls == {start_url}
    assert crawler.failed_urls == {}


@pytest.mark.asyncio
async def test_day3_crawl_respects_max_depth(day3_test_server):
    start_url = f"{day3_test_server}/"

    async with AsyncCrawler(max_concurrent=3, max_depth=1) as crawler:
        results = await crawler.crawl(
            start_urls=[start_url],
            max_pages=10,
            same_domain_only=True,
            show_progress=False,
        )

    assert set(results.keys()) == {
        f"{day3_test_server}/",
        f"{day3_test_server}/page1",
        f"{day3_test_server}/page2",
    }
    assert f"{day3_test_server}/deep" not in results
    assert "https://external.com/page" not in crawler.visited_urls


@pytest.mark.asyncio
async def test_day3_crawl_respects_max_pages(day3_test_server):
    start_url = f"{day3_test_server}/"

    async with AsyncCrawler(max_concurrent=3, max_depth=1) as crawler:
        results = await crawler.crawl(
            start_urls=[start_url],
            max_pages=2,
            same_domain_only=True,
            show_progress=False,
        )

    assert len(results) == 2
    assert start_url in results
    assert len(crawler.visited_urls) == 2


@pytest.mark.asyncio
async def test_day3_crawl_does_not_process_duplicate_links(day3_test_server):
    start_url = f"{day3_test_server}/"

    async with AsyncCrawler(max_concurrent=3, max_depth=1) as crawler:
        results = await crawler.crawl(
            start_urls=[start_url],
            max_pages=10,
            same_domain_only=True,
            show_progress=False,
        )

    assert list(results.keys()).count(f"{day3_test_server}/page1") == 1
    assert list(crawler.visited_urls).count(f"{day3_test_server}/page1") == 1


@pytest.mark.asyncio
async def test_day3_crawl_tracks_failed_urls(day3_test_server):
    start_url = f"{day3_test_server}/with-missing"

    async with AsyncCrawler(max_concurrent=3, max_depth=1) as crawler:
        results = await crawler.crawl(
            start_urls=[start_url],
            max_pages=10,
            same_domain_only=True,
            show_progress=False,
        )

    assert start_url in results
    assert f"{day3_test_server}/missing" not in results
    assert crawler.failed_urls == {
        f"{day3_test_server}/missing": "Failed to fetch HTML",
    }


def test_day3_crawler_normalizes_urls():
    crawler = AsyncCrawler()

    assert crawler._normalize_url("HTTPS://Example.com") == "https://example.com/"
    assert crawler._normalize_url("https://example.com#top") == "https://example.com/"
    assert crawler._normalize_url(" https://example.com/page ") == "https://example.com/page"


def test_day3_crawler_skips_normalized_duplicate_urls():
    crawler = AsyncCrawler()
    start_domains = {"example.com"}

    crawler.visited_urls.add("https://example.com/")

    assert crawler._should_crawl_url(
        url="https://example.com",
        start_domains=start_domains,
        same_domain_only=True,
        exclude_patterns=None,
        include_patterns=None,
    ) is False
