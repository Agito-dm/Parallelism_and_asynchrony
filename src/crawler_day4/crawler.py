import asyncio
import logging
import random
from time import perf_counter

import aiohttp

from crawler_day3.crawler import AsyncCrawler as BaseAsyncCrawler

from crawler_day4.rate_limiter import RateLimiter
from crawler_day4.robots_parser import RobotsParser

logger = logging.getLogger(__name__)


class AsyncCrawler(BaseAsyncCrawler):
    def __init__(
        self,
        max_concurrent: int = 10,
        max_depth: int = 2,
        max_per_domain: int = 2,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
        requests_per_second: float = 1.0,
        respect_robots: bool = True,
        min_delay: float = 0.0,
        jitter: float = 0.0,
        user_agent: str = "AsyncCrawler/1.0",
        per_domain_rate_limit: bool = True,
        max_retries: int = 2,
        backoff_base: float = 0.5,
    ) -> None:
        if min_delay < 0:
            raise ValueError("min_delay must be non-negative")

        if jitter < 0:
            raise ValueError("jitter must be non-negative")

        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        if backoff_base < 0:
            raise ValueError("backoff_base must be non-negative")

        super().__init__(
            max_concurrent=max_concurrent,
            max_depth=max_depth,
            max_per_domain=max_per_domain,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

        self.requests_per_second = requests_per_second
        self.min_delay = min_delay
        self.jitter = jitter
        self.respect_robots = respect_robots
        self.user_agent = user_agent
        self.per_domain_rate_limit = per_domain_rate_limit
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_count = 0

        effective_requests_per_second = requests_per_second

        if min_delay > 0:
            effective_requests_per_second = min(
                requests_per_second,
                1.0 / min_delay,
            )

        self.effective_requests_per_second = effective_requests_per_second

        self.rate_limiter = RateLimiter(
            requests_per_second=effective_requests_per_second,
            per_domain=per_domain_rate_limit,
        )
        self.robots_parser = RobotsParser()

        self.blocked_urls: dict[str, str] = {}
        self.delay_history: list[float] = []
        self.request_timestamps: list[float] = []

        self._crawl_delay_times: dict[str, float] = {}
        self._crawl_delay_locks: dict[str, asyncio.Lock] = {}

    def _reset_crawl_state(self) -> None:
        super()._reset_crawl_state()

        self.blocked_urls.clear()
        self.delay_history.clear()
        self.request_timestamps.clear()
        self.rate_limiter.reset()
        self.robots_parser.reset()
        self._crawl_delay_times.clear()
        self._crawl_delay_locks.clear()
        self.backoff_count = 0

    async def fetch_url(self, url: str) -> str:
        async with self._semaphore:
            logger.info("Start loading URL: %s", url)

            try:
                session = await self._get_session()
                headers = {"User-Agent": self.user_agent}

                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()

                    text = await response.text()

                    logger.info(
                        "Successfully loaded URL: %s | status=%s | bytes=%s",
                        url,
                        response.status,
                        len(text),
                    )

                    return text

            except aiohttp.ClientResponseError as error:
                logger.warning(
                    "HTTP error while loading URL: %s | status=%s | message=%s",
                    url,
                    error.status,
                    error.message,
                )

            except asyncio.TimeoutError:
                logger.warning("Timeout while loading URL: %s", url)

            except aiohttp.ClientError as error:
                logger.warning(
                    "Network error while loading URL: %s | error=%s",
                    url,
                    type(error).__name__,
                )

            return ""
    
    def _get_crawl_delay_lock(self, domain: str) -> asyncio.Lock:
        if domain not in self._crawl_delay_locks:
            self._crawl_delay_locks[domain] = asyncio.Lock()

        return self._crawl_delay_locks[domain]


    async def _wait_for_crawl_delay(self, url: str) -> None:
        if not self.respect_robots:
            return

        crawl_delay = self.robots_parser.get_crawl_delay(
            user_agent=self.user_agent,
            base_url=url,
        )

        if crawl_delay <= 0:
            return

        domain = self._get_domain(url)
        lock = self._get_crawl_delay_lock(domain)

        async with lock:
            now = perf_counter()
            last_request_time = self._crawl_delay_times.get(domain)

            if last_request_time is not None:
                elapsed = now - last_request_time
                wait_time = crawl_delay - elapsed

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self._crawl_delay_times[domain] = perf_counter()

    async def _wait_before_request(self, url: str) -> None:
        started_at = perf_counter()

        domain = self._get_domain(url)
        await self.rate_limiter.acquire(domain)
        await self._wait_for_crawl_delay(url)

        if self.jitter > 0:
            jitter_delay = random.uniform(0, self.jitter)
            await asyncio.sleep(jitter_delay)

        total_delay = perf_counter() - started_at
        self.delay_history.append(total_delay)

    def _record_request(self) -> None:
        self.request_timestamps.append(perf_counter())
    
    async def _is_allowed_by_robots(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        
        await self.robots_parser.fetch_robots(url)

        is_allowed = self.robots_parser.can_fetch(
            url,
            user_agent=self.user_agent,
        )

        if is_allowed:
            return True
        
        reason = f"Blocked by robots.txt for user-agent {self.user_agent}"
        self.blocked_urls[url] = reason
        self.queue.mark_failed(url, reason)

        logger.info("Blocked by robots.txt: %s", url)

        return False

    def _page_has_fetch_error(self, page_data: dict) -> bool:
        errors = page_data.get("errors", [])

        return "Failed to fetch HTML" in errors


    async def _sleep_before_retry(self, attempt: int) -> None:
        if self.backoff_base <= 0:
            return

        delay = self.backoff_base * (2 ** attempt)

        if self.jitter > 0:
            delay += random.uniform(0, self.jitter)

        self.backoff_count += 1
        await asyncio.sleep(delay)


    async def _fetch_with_backoff(self, url: str) -> dict:
        last_page_data: dict | None = None

        for attempt in range(self.max_retries + 1):
            await self._wait_before_request(url)
            self._record_request()

            try:
                page_data = await self.fetch_and_parse(url)
            except Exception as error:
                if attempt >= self.max_retries:
                    raise error

                await self._sleep_before_retry(attempt)
                continue

            if not self._page_has_fetch_error(page_data):
                return page_data

            last_page_data = page_data

            if attempt >= self.max_retries:
                return page_data

            await self._sleep_before_retry(attempt)

        if last_page_data is not None:
            return last_page_data

        return {
            "url": url,
            "title": "",
            "metadata": {},
            "text": "",
            "links": [],
            "images": [],
            "headings": {},
            "tables": [],
            "lists": [],
            "errors": ["Failed to fetch HTML"],
        }

    async def _crawl_single_url(self, url: str) -> dict | None:
        try:
            async with self.semaphore_manager.limit_for(url):
                is_allowed = await self._is_allowed_by_robots(url)

                if not is_allowed:
                    return None

                page_data = await self._fetch_with_backoff(url)

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

    def get_rate_stats(self) -> dict:
        average_delay = (
            sum(self.delay_history) / len(self.delay_history)
            if self.delay_history
            else 0.0
        )

        now = perf_counter()
        current_requests_per_second = sum(
            1
            for timestamp in self.request_timestamps
            if now - timestamp <= 1.0
        )

        return {
            "requests_per_second": self.requests_per_second,
            "effective_requests_per_second": self.effective_requests_per_second,
            "current_requests_per_second": current_requests_per_second,
            "average_delay": average_delay,
            "blocked_by_robots": len(self.blocked_urls),
            "total_requests": len(self.request_timestamps),
            "backoff_count": self.backoff_count,
        }

    def _print_progress(self, started_at: float) -> None:
        elapsed = max(perf_counter() - started_at, 0.000001)

        processed_count = len(self.processed_urls)
        failed_count = len(self.failed_urls)
        blocked_count = len(self.blocked_urls)
        speed = (processed_count + failed_count + blocked_count) / elapsed

        queue_stats = self.queue.get_stats()
        semaphore_stats = self.semaphore_manager.get_stats()
        rate_stats = self.get_rate_stats()

        print(
            "Progress | "
            f"processed={processed_count} | "
            f"queued={queue_stats['queued']} | "
            f"failed={failed_count} | "
            f"blocked={blocked_count} | "
            f"active={semaphore_stats['active_total']} | "
            f"speed={speed:.2f} pages/sec | "
            f"current_rps={rate_stats['current_requests_per_second']:.2f} | "
            f"avg_delay={rate_stats['average_delay']:.3f}s"
        )