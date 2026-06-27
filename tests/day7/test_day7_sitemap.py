import pytest

from crawler_day7.config import CrawlerConfig
from crawler_day7.crawler import AdvancedCrawler
from crawler_day7.sitemap import SitemapParser


class FakeResponse:
    def __init__(self, text: str, *, status: int = 200) -> None:
        self._text = text
        self.status = status

    async def text(self) -> str:
        return self._text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self, responses: dict[str, str | FakeResponse]) -> None:
        self.responses = responses
        self.calls = []

    def get(self, url: str, **kwargs):
        self.calls.append(url)

        response = self.responses[url]

        if isinstance(response, FakeResponse):
            return response

        return FakeResponse(response)


class FakeSitemapParser:
    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        assert sitemap_url == "https://example.com/sitemap.xml"

        return [
            "https://example.com/from-sitemap-1",
            "https://example.com/from-sitemap-2",
        ]


async def test_day7_sitemap_parser_extracts_urls_from_urlset():
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page-1</loc>
        </url>
        <url>
            <loc>https://example.com/page-2</loc>
        </url>
    </urlset>
    """

    session = FakeSession(
        {
            "https://example.com/sitemap.xml": sitemap_xml,
        }
    )
    parser = SitemapParser(session=session)

    urls = await parser.fetch_sitemap("https://example.com/sitemap.xml")

    assert urls == [
        "https://example.com/page-1",
        "https://example.com/page-2",
    ]
    assert session.calls == ["https://example.com/sitemap.xml"]


async def test_day7_sitemap_parser_supports_sitemap_index():
    index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://example.com/sitemap-1.xml</loc>
        </sitemap>
        <sitemap>
            <loc>https://example.com/sitemap-2.xml</loc>
        </sitemap>
    </sitemapindex>
    """

    sitemap_1_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page-1</loc>
        </url>
    </urlset>
    """

    sitemap_2_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page-2</loc>
        </url>
    </urlset>
    """

    session = FakeSession(
        {
            "https://example.com/sitemap.xml": index_xml,
            "https://example.com/sitemap-1.xml": sitemap_1_xml,
            "https://example.com/sitemap-2.xml": sitemap_2_xml,
        }
    )
    parser = SitemapParser(session=session)

    urls = await parser.fetch_sitemap("https://example.com/sitemap.xml")

    assert urls == [
        "https://example.com/page-1",
        "https://example.com/page-2",
    ]
    assert session.calls == [
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap-1.xml",
        "https://example.com/sitemap-2.xml",
    ]


async def test_day7_sitemap_parser_recursively_processes_nested_indexes():
    root_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://example.com/nested-index.xml</loc>
        </sitemap>
    </sitemapindex>
    """

    nested_index_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <sitemap>
            <loc>https://example.com/pages.xml</loc>
        </sitemap>
    </sitemapindex>
    """

    pages_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/final-page</loc>
        </url>
    </urlset>
    """

    session = FakeSession(
        {
            "https://example.com/sitemap.xml": root_index_xml,
            "https://example.com/nested-index.xml": nested_index_xml,
            "https://example.com/pages.xml": pages_xml,
        }
    )
    parser = SitemapParser(session=session)

    urls = await parser.fetch_sitemap("https://example.com/sitemap.xml")

    assert urls == ["https://example.com/final-page"]


async def test_day7_sitemap_parser_removes_duplicate_urls():
    sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://example.com/page</loc>
        </url>
        <url>
            <loc>https://example.com/page</loc>
        </url>
    </urlset>
    """

    session = FakeSession(
        {
            "https://example.com/sitemap.xml": sitemap_xml,
        }
    )
    parser = SitemapParser(session=session)

    urls = await parser.fetch_sitemap("https://example.com/sitemap.xml")

    assert urls == ["https://example.com/page"]


async def test_day7_sitemap_parser_raises_for_http_error():
    session = FakeSession(
        {
            "https://example.com/sitemap.xml": FakeResponse(
                "Not found",
                status=404,
            ),
        }
    )
    parser = SitemapParser(session=session)

    with pytest.raises(RuntimeError, match="Failed to fetch sitemap"):
        await parser.fetch_sitemap("https://example.com/sitemap.xml")


async def test_day7_advanced_crawler_collects_start_urls_from_config_and_sitemap():
    config = CrawlerConfig(
        start_urls=["https://example.com/start"],
        sitemap_urls=["https://example.com/sitemap.xml"],
        respect_robots=False,
    )
    crawler = AdvancedCrawler(
        config=config,
        sitemap_parser=FakeSitemapParser(),
        respect_robots=False,
    )

    urls = await crawler.collect_start_urls()

    assert urls == [
        "https://example.com/start",
        "https://example.com/from-sitemap-1",
        "https://example.com/from-sitemap-2",
    ]

    await crawler.close()
