from crawler_day7.config import CrawlerConfig
from crawler_day7.crawler import AdvancedCrawler


class FakeSitemapParser:
    async def fetch_sitemap(self, sitemap_url: str) -> list[str]:
        return [
            "https://example.com/blog/from-sitemap",
            "https://example.com/private/from-sitemap",
            "https://example.com/api/from-sitemap",
        ]


async def test_day7_collect_start_urls_applies_include_and_exclude_patterns():
    config = CrawlerConfig(
        start_urls=[
            "https://example.com/blog/start",
            "https://example.com/private/start",
            "https://example.com/api/start",
        ],
        sitemap_urls=["https://example.com/sitemap.xml"],
        include_patterns=["/blog/"],
        exclude_patterns=["private"],
        respect_robots=False,
    )

    crawler = AdvancedCrawler(
        config=config,
        sitemap_parser=FakeSitemapParser(),
        respect_robots=False,
    )

    urls = await crawler.collect_start_urls()

    assert urls == [
        "https://example.com/blog/start",
        "https://example.com/blog/from-sitemap",
    ]

    await crawler.close()


async def test_day7_collect_start_urls_keeps_all_urls_without_filters():
    config = CrawlerConfig(
        start_urls=[
            "https://example.com/page",
            "https://example.com/page",
        ],
        sitemap_urls=[],
        include_patterns=[],
        exclude_patterns=[],
        respect_robots=False,
    )

    crawler = AdvancedCrawler(
        config=config,
        respect_robots=False,
    )

    urls = await crawler.collect_start_urls()

    assert urls == [
        "https://example.com/page",
    ]

    await crawler.close()
