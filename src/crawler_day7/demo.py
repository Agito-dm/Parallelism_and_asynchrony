import asyncio
from pathlib import Path

from crawler_day7.crawler import AdvancedCrawler


CONFIG_PATH = Path("config/day7_config.json")
JSON_REPORT_PATH = Path("data/day7/report.json")
HTML_REPORT_PATH = Path("data/day7/report.html")


async def run_demo() -> None:
    crawler = AdvancedCrawler.from_config(CONFIG_PATH)

    try:
        await crawler.crawl_from_config()

        crawler.export_to_json(JSON_REPORT_PATH)
        crawler.export_to_html_report(HTML_REPORT_PATH)

        stats = crawler.get_stats()

        print("Day 7 demo finished")
        print(f"Total pages: {stats.get('total_pages', 0)}")
        print(f"Successful: {stats.get('successful', 0)}")
        print(f"Failed: {stats.get('failed', 0)}")
        print(f"JSON report: {JSON_REPORT_PATH}")
        print(f"HTML report: {HTML_REPORT_PATH}")

    finally:
        await crawler.close()


def main() -> None:
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
