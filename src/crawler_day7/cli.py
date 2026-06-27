import argparse
import asyncio
import logging
from pathlib import Path
from typing import Sequence

from crawler_day7.config import CrawlerConfig
from crawler_day7.crawler import AdvancedCrawler, create_storage_from_config

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run advanced async crawler.",
    )

    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to crawler JSON config file.",
    )

    parser.add_argument(
        "--config",
        dest="config_file",
        default=None,
        help="Path to crawler JSON config file.",
    )

    parser.add_argument(
        "--urls",
        nargs="+",
        default=None,
        help="Start URLs for direct CLI mode.",
    )
    parser.add_argument(
        "--max-pages",
        dest="max_pages",
        type=int,
        default=None,
        help="Maximum number of pages to crawl.",
    )
    parser.add_argument(
        "--max-depth",
        dest="max_depth",
        type=int,
        default=None,
        help="Maximum crawl depth.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save crawled data.",
    )
    parser.add_argument(
        "--respect-robots",
        dest="respect_robots",
        action="store_true",
        help="Respect robots.txt rules.",
    )
    parser.add_argument(
        "--rate-limit",
        dest="rate_limit",
        type=float,
        default=None,
        help="Requests per second limit.",
    )

    parser.add_argument(
        "--json-report",
        dest="json_report",
        default=None,
        help="Path to save JSON statistics report.",
    )
    parser.add_argument(
        "--html-report",
        dest="html_report",
        default=None,
        help="Path to save HTML statistics report.",
    )
    parser.add_argument(
        "--no-progress",
        dest="show_progress",
        action="store_false",
        help="Disable crawl progress output.",
    )

    parser.set_defaults(show_progress=True)

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = build_parser()

    return parser.parse_args(argv)


def _build_config_from_args(args: argparse.Namespace) -> CrawlerConfig:
    config = CrawlerConfig.default()

    if args.urls is not None:
        config.start_urls = args.urls

    if args.max_pages is not None:
        config.max_pages = args.max_pages

    if args.max_depth is not None:
        config.max_depth = args.max_depth

    if args.rate_limit is not None:
        config.rate_limit = args.rate_limit

    config.respect_robots = args.respect_robots

    if args.output is not None:
        config.output.filename = args.output
        config.output.type = _infer_output_type(args.output)

    config.validate()

    return config


def _infer_output_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".csv":
        return "csv"

    if suffix in {".sqlite", ".db"}:
        return "sqlite"

    return "jsonl"


async def run_from_args(args: argparse.Namespace) -> dict:
    config_path = args.config_file or args.config

    if config_path:
        crawler = AdvancedCrawler.from_config(config_path)
    else:
        if not args.urls:
            raise ValueError("Either config file or --urls must be provided")

        config = _build_config_from_args(args)
        storage = create_storage_from_config(config)

        crawler = AdvancedCrawler(
            config=config,
            storage=storage,
            max_depth=config.max_depth,
            max_concurrent=config.max_concurrent,
            requests_per_second=config.rate_limit,
            respect_robots=config.respect_robots,
        )

    try:
        if args.max_pages is None and config_path:
            await crawler.crawl_from_config()
        else:
            urls = await crawler.collect_start_urls()

            await crawler.crawl(
                urls,
                max_pages=args.max_pages,
                show_progress=args.show_progress,
            )

        if args.json_report:
            crawler.export_to_json(args.json_report)

        if args.html_report:
            crawler.export_to_html_report(args.html_report)

        return crawler.get_stats()

    finally:
        await crawler.close()


async def async_main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        stats = await run_from_args(args)
    except Exception as error:
        logger.exception("Crawler CLI failed: %s", error)
        return 1

    print("Crawler finished")
    print(f"Total pages: {stats.get('total_pages', 0)}")
    print(f"Successful: {stats.get('successful', 0)}")
    print(f"Failed: {stats.get('failed', 0)}")

    if args.json_report:
        print(f"JSON report: {Path(args.json_report)}")

    if args.html_report:
        print(f"HTML report: {Path(args.html_report)}")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return asyncio.run(async_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
