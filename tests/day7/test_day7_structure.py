import argparse

from crawler_day6.crawler import AsyncCrawler as Day6Crawler
from crawler_day7 import AdvancedCrawler, CrawlerConfig, CrawlerStats, SitemapParser
from crawler_day7.cli import build_parser
from crawler_day7.config import LoggingConfig, OutputConfig
from crawler_day7.reporting import export_stats_to_html, export_stats_to_json


def test_day7_config_can_be_created():
    config = CrawlerConfig.default()

    assert config.max_pages == 100
    assert config.max_depth == 2
    assert config.max_concurrent == 5
    assert config.rate_limit == 1.0
    assert config.output.type == "jsonl"
    assert config.logging.level == "INFO"


def test_day7_config_rejects_invalid_values():
    config = CrawlerConfig(max_pages=0)

    try:
        config.validate()
    except ValueError as error:
        assert "max_pages" in str(error)
    else:
        raise AssertionError("Expected ValueError")


def test_day7_output_and_logging_config_can_be_created():
    output = OutputConfig(type="csv", filename="data/results.csv")
    logging_config = LoggingConfig(level="DEBUG", filename="logs/test.log")

    assert output.type == "csv"
    assert output.filename == "data/results.csv"
    assert logging_config.level == "DEBUG"
    assert logging_config.filename == "logs/test.log"


def test_day7_stats_can_record_success_and_failure():
    stats = CrawlerStats()

    stats.start()
    stats.record_success("https://example.com/page", 200)
    stats.record_failure("https://example.org/missing", 404)
    stats.finish()

    data = stats.to_dict()

    assert data["total_pages"] == 2
    assert data["successful"] == 1
    assert data["failed"] == 1
    assert data["status_codes"] == {"200": 1, "404": 1}
    assert data["top_domains"] == {
        "example.com": 1,
        "example.org": 1,
    }
    assert data["duration_seconds"] >= 0


def test_day7_sitemap_parser_can_be_created():
    parser = SitemapParser()

    assert parser is not None


def test_day7_advanced_crawler_extends_day6_crawler():
    crawler = AdvancedCrawler(
        respect_robots=False,
        max_concurrent=3,
    )

    assert isinstance(crawler, Day6Crawler)
    assert crawler.get_stats()["total_pages"] == 0


def test_day7_report_exports_create_files(tmp_path):
    stats = {
        "total_pages": 2,
        "successful": 2,
        "failed": 0,
    }

    json_path = tmp_path / "stats.json"
    html_path = tmp_path / "report.html"

    export_stats_to_json(stats, json_path)
    export_stats_to_html(stats, html_path)

    assert json_path.exists()
    assert html_path.exists()

    assert '"total_pages": 2' in json_path.read_text(encoding="utf-8")
    assert "<html" in html_path.read_text(encoding="utf-8")


def test_day7_cli_parser_accepts_required_arguments():
    parser = build_parser()

    assert isinstance(parser, argparse.ArgumentParser)

    args = parser.parse_args(
        [
            "--urls",
            "https://example.com",
            "--max-pages",
            "10",
            "--max-depth",
            "2",
            "--output",
            "data/results.jsonl",
            "--respect-robots",
            "--rate-limit",
            "2.5",
        ]
    )

    assert args.urls == ["https://example.com"]
    assert args.max_pages == 10
    assert args.max_depth == 2
    assert args.output == "data/results.jsonl"
    assert args.respect_robots is True
    assert args.rate_limit == 2.5
