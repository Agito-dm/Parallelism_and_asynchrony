import asyncio

from crawler_day4.crawler import AsyncCrawler


async def main() -> None:
    start_urls = [
        "https://example.com/",
    ]

    async with AsyncCrawler(
        max_concurrent=3,
        max_depth=1,
        max_per_domain=2,
        requests_per_second=2.0,
        respect_robots=True,
        min_delay=0.5,
        jitter=0.1,
        user_agent="MyBot/1.0",
        max_retries=2,
        backoff_base=0.5,
    ) as crawler:
        print("Starting Day 4 crawler demo...")
        print(f"Start URLs: {start_urls}")

        await crawler.crawl(
            start_urls,
            max_pages=5,
            same_domain_only=True,
            show_progress=True,
        )

        stats = crawler.get_rate_stats()

        print("\nDemo finished")
        print("=" * 60)

        print("\nRate stats:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

        print("\nProcessed URLs:")
        for url in crawler.processed_urls:
            print(f"  OK: {url}")

        print("\nFailed URLs:")
        for url, reason in crawler.failed_urls.items():
            print(f"  FAILED: {url} | {reason}")

        print("\nBlocked by robots.txt:")
        for url, reason in crawler.blocked_urls.items():
            print(f"  BLOCKED: {url} | {reason}")


if __name__ == "__main__":
    asyncio.run(main())