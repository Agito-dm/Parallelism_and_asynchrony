import asyncio
import re
from time import perf_counter
from urllib.parse import urldefrag, urlparse, urlunparse

from crawler_day2.crawler import AsyncCrawler as BaseAsyncCrawler
from crawler_day3.crawler_queue import CrawlerQueue
from crawler_day3.semaphore_manager import SemaphoreManager


class AsyncCrawler(BaseAsyncCrawler):
    def __init__(
        self,
        max_concurrent: int = 10,
        max_depth: int = 2,
        max_per_domain: int = 2,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        if max_depth < 0:
            raise ValueError("max_depth must be non-negative")

        super().__init__(
            max_concurrent=max_concurrent,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

        self.max_depth = max_depth
        self.queue = CrawlerQueue()
        self.semaphore_manager = SemaphoreManager(
            max_global=max_concurrent,
            max_per_domain=max_per_domain,
        )

        self.visited_urls: set[str] = set()
        self.failed_urls: dict[str, str] = {}
        self.processed_urls: dict[str, dict] = {}

    def _reset_crawl_state(self) -> None:
        self.queue = CrawlerQueue()
        self.visited_urls.clear()
        self.failed_urls.clear()
        self.processed_urls.clear()

    def _get_domain(self, url: str) -> str:
        normalized_url = self._normalize_url(url)
        parsed = urlparse(normalized_url)
        return parsed.netloc

    def _is_valid_url(self, url: str) -> bool:
        normalized_url = self._normalize_url(url)
        parsed = urlparse(normalized_url)

        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    
    def _normalize_url(self, url: str) -> str:
        cleaned_url = url.strip()
        cleaned_url, _fragment = urldefrag(cleaned_url)

        parsed = urlparse(cleaned_url)

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"

        return urlunparse(
            (
                scheme,
                netloc,
                path,
                "",
                parsed.query,
                "",
            )
        )

    def _get_start_domains(self, start_urls: list[str]) -> set[str]:
        return {
            self._get_domain(url)
            for url in start_urls
            if self._is_valid_url(url)
        }

    def _matches_patterns(
        self,
        url: str,
        patterns: list[str] | None,
    ) -> bool:
        if not patterns:
            return False

        return any(re.search(pattern, url) for pattern in patterns)

    def _should_crawl_url(
        self,
        url: str,
        start_domains: set[str],
        same_domain_only: bool,
        exclude_patterns: list[str] | None,
        include_patterns: list[str] | None,
    ) -> bool:
        normalized_url = self._normalize_url(url)

        if not self._is_valid_url(normalized_url):
            return False

        if normalized_url in self.visited_urls:
            return False

        if normalized_url in self.processed_urls:
            return False

        if normalized_url in self.failed_urls:
            return False

        if same_domain_only and self._get_domain(normalized_url) not in start_domains:
            return False

        if self._matches_patterns(normalized_url, exclude_patterns):
            return False

        if include_patterns and not self._matches_patterns(normalized_url, include_patterns):
            return False

        return True

    async def _crawl_single_url(self, url: str) -> dict | None:
        try:
            async with self.semaphore_manager.limit_for(url):
                page_data = await self.fetch_and_parse(url)
        except Exception as error:
            error_message = f"{type(error).__name__}: {error}"
            self.failed_urls[url] = error_message
            self.queue.mark_failed(url, error_message)
            return None

        errors = page_data.get("errors", [])

        if "Failed to fetch HTML" in errors:
            error_message = "; ".join(errors)
            self.failed_urls[url] = error_message
            self.queue.mark_failed(url, error_message)
            return None

        self.processed_urls[url] = page_data
        self.queue.mark_processed(url)

        return page_data

    def _add_discovered_links(
        self,
        links: list[str],
        current_depth: int,
        start_domains: set[str],
        same_domain_only: bool,
        exclude_patterns: list[str] | None,
        include_patterns: list[str] | None,
    ) -> int:
        next_depth = current_depth + 1

        if next_depth > self.max_depth:
            return 0

        added_count = 0

        for link in links:
            normalized_link = self._normalize_url(link)

            if not self._should_crawl_url(
                url=normalized_link,
                start_domains=start_domains,
                same_domain_only=same_domain_only,
                exclude_patterns=exclude_patterns,
                include_patterns=include_patterns,
            ):
                continue

            was_added = self.queue.add_url(
                normalized_link,
                priority=-next_depth,
                depth=next_depth,
            )

            if was_added:
                added_count += 1

        return added_count

    def _print_progress(self, started_at: float) -> None:
        elapsed = max(perf_counter() - started_at, 0.000001)
        processed_count = len(self.processed_urls)
        failed_count = len(self.failed_urls)
        speed = (processed_count + failed_count) / elapsed

        queue_stats = self.queue.get_stats()
        semaphore_stats = self.semaphore_manager.get_stats()

        print(
            "Progress | "
            f"processed={processed_count} | "
            f"queued={queue_stats['queued']} | "
            f"failed={failed_count} | "
            f"active={semaphore_stats['active_total']} | "
            f"speed={speed:.2f} pages/sec"
        )

    async def crawl(
        self,
        start_urls: list[str],
        max_pages: int = 100,
        same_domain_only: bool = False,
        exclude_patterns: list[str] | None = None,
        include_patterns: list[str] | None = None,
        show_progress: bool = True,
    ) -> dict[str, dict]:
        if max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        self._reset_crawl_state()

        start_domains = self._get_start_domains(start_urls)

        if not start_domains:
            return {}

        for url in start_urls:
            normalized_url = self._normalize_url(url)

            if not self._should_crawl_url(
                url=normalized_url,
                start_domains=start_domains,
                same_domain_only=same_domain_only,
                exclude_patterns=exclude_patterns,
                include_patterns=include_patterns,
            ):
                continue

            self.queue.add_url(normalized_url, priority=0, depth=0)

        started_at = perf_counter()

        while len(self.visited_urls) < max_pages:
            batch: list[tuple[str, int]] = []

            while len(batch) < self.max_concurrent and len(self.visited_urls) < max_pages:
                url = await self.queue.get_next()

                if url is None:
                    break

                if not self._should_crawl_url(
                    url=url,
                    start_domains=start_domains,
                    same_domain_only=same_domain_only,
                    exclude_patterns=exclude_patterns,
                    include_patterns=include_patterns,
                ):
                    continue

                self.visited_urls.add(url)
                batch.append((url, self.queue.get_depth(url)))

            if not batch:
                break

            tasks = [
                asyncio.create_task(self._crawl_single_url(url))
                for url, _depth in batch
            ]

            page_results = await asyncio.gather(*tasks)

            for (_url, depth), page_data in zip(batch, page_results):
                if page_data is None:
                    continue

                self._add_discovered_links(
                    links=page_data.get("links", []),
                    current_depth=depth,
                    start_domains=start_domains,
                    same_domain_only=same_domain_only,
                    exclude_patterns=exclude_patterns,
                    include_patterns=include_patterns,
                )

            if show_progress:
                self._print_progress(started_at)

        return self.processed_urls
