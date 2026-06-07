import asyncio
import json
from pathlib import Path


from crawler_day5.crawler import AsyncCrawler
from crawler_day5.retry_strategy import RetryStrategy


class DemoResponse:
    def __init__(self, status: int, text: str = "") -> None:
        self.status = status
        self._text = text or (
            "<html>"
            "<head><title>Demo page</title></head>"
            "<body>Hello from demo</body>"
            "</html>"
        )

    async def text(self) -> str:
        return self._text


class DemoRequestContext:
    def __init__(self, response: DemoResponse) -> None:
        self.response = response

    async def __aenter__(self) -> DemoResponse:
        return self.response

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        return None


class DemoSession:
    def __init__(self, responses_by_url: dict[str, list[DemoResponse]]) -> None:
        self.responses_by_url = responses_by_url
        self.calls_by_url: dict[str, int] = {}

    def get(
        self,
        url: str,
        headers: dict | None = None,
        timeout=None,
    ) -> DemoRequestContext:
        current_calls = self.calls_by_url.get(url, 0)
        self.calls_by_url[url] = current_calls + 1

        responses = self.responses_by_url[url]
        response = responses[min(current_calls, len(responses) - 1)]

        print(
            f"HTTP demo request | url={url} | "
            f"attempt={current_calls + 1} | status={response.status}"
        )

        return DemoRequestContext(response)


async def main() -> None:
    success_url = "https://example.com/success"
    temporary_url = "https://example.com/temporary-503"
    missing_url = "https://example.com/missing-404"
    rate_limited_url = "https://example.com/rate-limited-429"

    fake_session = DemoSession(
        {
            success_url: [
                DemoResponse(
                    200,
                    "<html><head><title>Success</title></head>"
                    "<body>Successful page</body></html>",
                ),
            ],
            temporary_url: [
                DemoResponse(503),
                DemoResponse(
                    200,
                    "<html><head><title>Recovered after 503</title></head>"
                    "<body>Recovered page</body></html>",
                ),
            ],
            missing_url: [
                DemoResponse(404),
            ],
            rate_limited_url: [
                DemoResponse(429),
                DemoResponse(429),
                DemoResponse(429),
            ],
        }
    )

    retry_strategy = RetryStrategy(
        max_retries=2,
        backoff_factor=2.0,
        base_delay=0.1,
    )

    async with AsyncCrawler(
        max_concurrent=2,
        max_depth=0,
        requests_per_second=1000.0,
        respect_robots=False,
        user_agent="Day5DemoBot/1.0",
        retry_strategy=retry_strategy,
        total_timeout=1.0,
        timeout_backoff_factor=2.0,
    ) as crawler:

        async def fake_get_session() -> DemoSession:
            return fake_session

        crawler._get_session = fake_get_session

        start_urls = [
            success_url,
            temporary_url,
            missing_url,
            rate_limited_url,
        ]

        print("Starting Day 5 crawler demo...")
        print("=" * 70)

        await crawler.crawl(
            start_urls,
            max_pages=4,
            show_progress=True,
        )

        print("\nDemo finished")
        print("=" * 70)

        print("\nProcessed URLs:")
        for url, page_data in crawler.processed_urls.items():
            print(f"  OK: {url} | title={page_data.get('title')}")

        print("\nFailed URLs:")
        for url, reason in crawler.failed_urls.items():
            print(f"  FAILED: {url} | reason={reason}")

        print("\nHTTP calls:")
        for url, calls in fake_session.calls_by_url.items():
            print(f"  {url}: {calls}")

        print("\nRate stats:")
        for key, value in crawler.get_rate_stats().items():
            print(f"  {key}: {value}")

        print("\nError stats:")
        for key, value in crawler.get_error_stats().items():
            print(f"  {key}: {value}")

        report = {
            "rate_stats": crawler.get_rate_stats(),
            "error_report": crawler.get_error_report(),
            "processed_urls": list(crawler.processed_urls.keys()),
            "failed_urls": dict(crawler.failed_urls),
            "http_calls": dict(fake_session.calls_by_url),
        }

        output_path = Path("data") / "day5_error_report.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        print(f"\nError report saved to: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
