import argparse
import asyncio
import json
import time
import tracemalloc
from pathlib import Path
from typing import Sequence

from crawler_day7.crawler import AdvancedCrawler


HTML_TEMPLATE = """
<html>
    <head><title>Benchmark page</title></head>
    <body>Benchmark content</body>
</html>
"""


class FakeResponse:
    def __init__(
        self,
        html: str = HTML_TEMPLATE,
        *,
        status: int = 200,
        delay: float = 0.0,
    ) -> None:
        self.html = html
        self.status = status
        self.delay = delay
        self.headers = {"Content-Type": "text/html"}

    async def text(self) -> str:
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return self.html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self, responses: dict[str, FakeResponse]) -> None:
        self.responses = responses

    def get(self, url: str, **kwargs):
        return self.responses[url]


def build_urls(page_count: int) -> list[str]:
    return [
        f"https://example.com/page-{index}"
        for index in range(page_count)
    ]


async def run_async_benchmark(
    *,
    page_count: int,
    max_concurrent: int,
    delay: float,
) -> dict:
    urls = build_urls(page_count)

    session = FakeSession(
        {
            url: FakeResponse(delay=delay)
            for url in urls
        }
    )

    crawler = AdvancedCrawler(
        respect_robots=False,
        requests_per_second=100_000,
        max_concurrent=max_concurrent,
        max_depth=0,
    )

    async def fake_get_session():
        return session

    crawler._get_session = fake_get_session

    tracemalloc.start()
    start = time.perf_counter()

    try:
        await crawler.crawl(
            urls,
            max_pages=page_count,
            show_progress=False,
        )

        duration = time.perf_counter() - start
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        stats = crawler.get_stats()

    finally:
        tracemalloc.stop()
        await crawler.close()

    pages_per_second = page_count / duration if duration > 0 else 0.0

    return {
        "page_count": page_count,
        "max_concurrent": max_concurrent,
        "delay": delay,
        "async_duration_seconds": duration,
        "async_pages_per_second": pages_per_second,
        "async_stats": stats,
        "current_memory_kb": current_memory / 1024,
        "peak_memory_kb": peak_memory / 1024,
    }


def run_sync_baseline(
    *,
    page_count: int,
    delay: float,
) -> dict:
    start = time.perf_counter()

    for _ in range(page_count):
        if delay > 0:
            time.sleep(delay)

        _ = HTML_TEMPLATE

    duration = time.perf_counter() - start
    pages_per_second = page_count / duration if duration > 0 else 0.0

    return {
        "sync_duration_seconds": duration,
        "sync_pages_per_second": pages_per_second,
    }


async def run_benchmark(
    *,
    page_count: int,
    max_concurrent: int,
    delay: float,
) -> dict:
    async_result = await run_async_benchmark(
        page_count=page_count,
        max_concurrent=max_concurrent,
        delay=delay,
    )
    sync_result = run_sync_baseline(
        page_count=page_count,
        delay=delay,
    )

    result = {
        **async_result,
        **sync_result,
    }

    sync_duration = result["sync_duration_seconds"]
    async_duration = result["async_duration_seconds"]

    if async_duration > 0:
        result["speedup_vs_sync"] = sync_duration / async_duration
    else:
        result["speedup_vs_sync"] = 0.0

    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run crawler_day7 performance benchmark.",
    )

    parser.add_argument(
        "--pages",
        type=int,
        default=100,
        help="Number of fake pages to crawl.",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent crawler tasks.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.01,
        help="Artificial response delay in seconds.",
    )
    parser.add_argument(
        "--json-output",
        default=None,
        help="Optional path to save benchmark results as JSON.",
    )

    return parser


async def async_main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    result = await run_benchmark(
        page_count=args.pages,
        max_concurrent=args.max_concurrent,
        delay=args.delay,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    if args.json_output:
        path = Path(args.json_output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
