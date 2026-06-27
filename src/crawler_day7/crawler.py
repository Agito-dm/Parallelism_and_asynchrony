import re

from pathlib import Path
from typing import Any

from crawler_day6.crawler import AsyncCrawler as BaseAsyncCrawler
from crawler_day6.storage import CSVStorage, DataStorage, JSONStorage, SQLiteStorage

from crawler_day7.config import CrawlerConfig, load_config
from crawler_day7.logging_config import setup_logging
from crawler_day7.reporting import export_stats_to_html, export_stats_to_json
from crawler_day7.stats import CrawlerStats
from crawler_day7.sitemap import SitemapParser


def create_storage_from_config(config: CrawlerConfig) -> DataStorage:
    output_type = config.output.type
    output_filename = config.output.filename

    if output_type == "jsonl":
        return JSONStorage(output_filename)

    if output_type == "csv":
        return CSVStorage(output_filename)

    if output_type == "sqlite":
        return SQLiteStorage(output_filename)

    raise ValueError(f"Unsupported output type: {output_type}")


class AdvancedCrawler(BaseAsyncCrawler):
    def __init__(
        self,
        *args,
        config: CrawlerConfig | None = None,
        sitemap_parser: SitemapParser | None = None,
        **kwargs,
    ) -> None:
        self.config = config or CrawlerConfig.default()
        self.config.validate()

        self.advanced_stats = CrawlerStats()
        self.sitemap_parser = sitemap_parser or SitemapParser()

        super().__init__(*args, **kwargs)

    @classmethod
    def from_config(cls, filename: str | Path) -> "AdvancedCrawler":
        config = load_config(filename)

        setup_logging(
            level=config.logging.level,
            filename=config.logging.filename,
        )

        storage = create_storage_from_config(config)

        return cls(
            config=config,
            storage=storage,
            max_depth=config.max_depth,
            max_concurrent=config.max_concurrent,
            requests_per_second=config.rate_limit,
            respect_robots=config.respect_robots,
        )

    async def crawl(
        self,
        start_urls: list[str] | None = None,
        *args,
        max_pages: int | None = None,
        **kwargs,
    ):
        urls = start_urls if start_urls is not None else self.config.start_urls
        pages_limit = max_pages if max_pages is not None else self.config.max_pages

        self.advanced_stats.start()

        try:
            return await super().crawl(
                urls,
                *args,
                max_pages=pages_limit,
                **kwargs,
            )
        finally:
            self.advanced_stats.finish()

    async def crawl_from_config(self):
        urls = await self.collect_start_urls()

        return await self.crawl(
            urls,
            max_pages=self.config.max_pages,
        )

    async def fetch_and_parse(self, url: str) -> dict | None:
        page_data = await super().fetch_and_parse(url)

        self._record_page_stats(url, page_data)

        return page_data

    def _record_page_stats(self, url: str, page_data: Any) -> None:
        if self._is_page_data_successful(page_data):
            storage_data = self._build_storage_data(url, page_data)

            self.advanced_stats.record_success(
                storage_data["url"],
                storage_data.get("status_code") or 200,
            )
            return

        status_code = None

        if isinstance(page_data, dict):
            status_code = page_data.get("status_code")

            if status_code is None:
                response_metadata = self._get_response_metadata(url, page_data)
                status_code = response_metadata.get("status_code")

        self.advanced_stats.record_failure(
            url,
            status_code,
        )

    def get_stats(self) -> dict:
        return self.advanced_stats.to_dict()

    def export_to_json(self, filename: str) -> None:
        export_stats_to_json(self.get_stats(), filename)

    def export_to_html_report(self, filename: str) -> None:
        export_stats_to_html(self.get_stats(), filename)
    
    async def collect_start_urls(self) -> list[str]:
        urls: list[str] = list(self.config.start_urls)

        for sitemap_url in self.config.sitemap_urls:
            sitemap_urls = await self.sitemap_parser.fetch_sitemap(sitemap_url)
            urls.extend(sitemap_urls)

        return self._deduplicate_and_filter_urls(urls)

    def _matches_config_pattern(self, url: str, pattern: str) -> bool:
        try:
            return re.search(pattern, url) is not None
        except re.error:
            return pattern in url

    def _is_allowed_by_config_filters(self, url: str) -> bool:
        include_patterns = getattr(self.config, "include_patterns", []) or []
        exclude_patterns = getattr(self.config, "exclude_patterns", []) or []

        if include_patterns:
            has_include_match = any(
                self._matches_config_pattern(url, pattern)
                for pattern in include_patterns
            )

            if not has_include_match:
                return False

        has_exclude_match = any(
            self._matches_config_pattern(url, pattern)
            for pattern in exclude_patterns
        )

        if has_exclude_match:
            return False

        return True

    def _deduplicate_and_filter_urls(self, urls: list[str]) -> list[str]:
        unique_urls: list[str] = []
        seen: set[str] = set()

        for url in urls:
            if url in seen:
                continue

            seen.add(url)

            if self._is_allowed_by_config_filters(url):
                unique_urls.append(url)

        return unique_urls
