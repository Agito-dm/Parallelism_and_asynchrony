import asyncio
import logging
from pprint import pprint
from time import perf_counter

from crawler_day2.crawler import AsyncCrawler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


URLS = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://www.python.org",
]


def build_summary(page_data: dict) -> dict:
    return {
        "url": page_data["url"],
        "title": page_data["title"],
        "text_length": len(page_data["text"]),
        "links_count": len(page_data["links"]),
        "images_count": len(page_data["images"]),
        "headings_count": len(page_data["headings"]),
        "tables_count": len(page_data["tables"]),
        "lists_count": len(page_data["lists"]),
        "links": page_data["links"][:5],
        "errors": page_data["errors"],
    }


async def main() -> None:
    start = perf_counter()

    async with AsyncCrawler(max_concurrent=3) as crawler:
        tasks = [
            asyncio.create_task(crawler.fetch_and_parse(url))
            for url in URLS
        ]
        pages = await asyncio.gather(*tasks)

    elapsed = perf_counter() - start

    print()
    print("Crawler Day 2 summary")
    print("=====================")

    for page_data in pages:
        summary = build_summary(page_data)
        pprint(summary, sort_dicts=False)
        print("-" * 80)

    print(f"Total pages: {len(pages)}")
    print(f"Total time: {elapsed:.2f} sec")


if __name__ == "__main__":
    asyncio.run(main())