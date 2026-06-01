import asyncio
import json
import logging
from pathlib import Path
from pprint import pprint

from crawler_day3.crawler import AsyncCrawler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


START_URLS = [
    "https://www.python.org",
]

OUTPUT_PATH = Path("data/day3_results.json")


def build_page_summary(url: str, page_data: dict) -> dict:
    return {
        "url": url,
        "title": page_data.get("title", ""),
        "text_length": len(page_data.get("text", "")),
        "links_count": len(page_data.get("links", [])),
        "images_count": len(page_data.get("images", [])),
        "headings_count": len(page_data.get("headings", [])),
        "tables_count": len(page_data.get("tables", [])),
        "lists_count": len(page_data.get("lists", [])),
        "errors": page_data.get("errors", []),
    }


def save_results(results: dict[str, dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
        )


async def main() -> None:
    async with AsyncCrawler(
        max_concurrent=5,
        max_depth=1,
        max_per_domain=2,
    ) as crawler:
        results = await crawler.crawl(
            start_urls=START_URLS,
            max_pages=10,
            same_domain_only=True,
            exclude_patterns=[
                r"/accounts",
                r"/users",
                r"\.pdf$",
                r"\.zip$",
            ],
            include_patterns=None,
            show_progress=True,
        )

        save_results(results, OUTPUT_PATH)

        print()
        print("Crawler Day 3 summary")
        print("=====================")
        print(f"Start URLs: {START_URLS}")
        print(f"Processed pages: {len(results)}")
        print(f"Visited URLs: {len(crawler.visited_urls)}")
        print(f"Failed URLs: {len(crawler.failed_urls)}")
        print(f"Saved to: {OUTPUT_PATH}")
        print()

        print("Queue stats:")
        pprint(crawler.queue.get_stats(), sort_dicts=False)
        print()

        print("Semaphore stats:")
        pprint(crawler.semaphore_manager.get_stats(), sort_dicts=False)
        print()

        print("Processed pages summary:")
        for url, page_data in results.items():
            pprint(build_page_summary(url, page_data), sort_dicts=False)
            print("-" * 80)

        if crawler.failed_urls:
            print()
            print("Failed URLs:")
            pprint(crawler.failed_urls, sort_dicts=False)


if __name__ == "__main__":
    asyncio.run(main())
