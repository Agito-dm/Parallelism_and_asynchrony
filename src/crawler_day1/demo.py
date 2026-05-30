import asyncio
import logging
from time import perf_counter

from crawler_day1.crawler import AsyncCrawler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


URLS = [
    "https://example.com",
    "https://httpbin.org/get",
    "https://httpbin.org/delay/1",
    "https://httpbin.org/delay/2",
    "https://httpbin.org/status/404",
]


async def load_parallel(urls: list[str]) -> dict[str, str]:
    async with AsyncCrawler(max_concurrent=5) as crawler:
        return await crawler.fetch_urls(urls)


async def load_sequential(urls: list[str]) -> dict[str, str]:
    async with AsyncCrawler(max_concurrent=1) as crawler:
        results: dict[str, str] = {}

        for url in urls:
            results[url] = await crawler.fetch_url(url)

        return results


def print_results(title: str, results: dict[str, str], elapsed: float) -> None:
    print()
    print(title)
    print("-" * len(title))

    for url, page in results.items():
        status = "OK" if page else "ERROR"
        print(f"{status:5} | {url}")

    print(f"Total time: {elapsed:.2f} sec")


async def main() -> None:
    start = perf_counter()
    sequential_results = await load_sequential(URLS)
    sequential_time = perf_counter() - start

    start = perf_counter()
    parallel_results = await load_parallel(URLS)
    parallel_time = perf_counter() - start

    print_results("Sequential loading", sequential_results, sequential_time)
    print_results("Parallel loading", parallel_results, parallel_time)

    print()
    print(f"Parallel is faster by: {sequential_time - parallel_time:.2f} sec")


if __name__ == "__main__":
    asyncio.run(main())
