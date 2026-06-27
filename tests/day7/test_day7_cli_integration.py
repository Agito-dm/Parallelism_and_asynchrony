from pathlib import Path

from crawler_day7 import cli


def test_day7_cli_parser_accepts_config_reports_and_max_pages():
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "config/day7_config.json",
            "--json-report",
            "data/report.json",
            "--html-report",
            "data/report.html",
            "--max-pages",
            "5",
            "--no-progress",
        ]
    )

    assert args.config == "config/day7_config.json"
    assert args.json_report == "data/report.json"
    assert args.html_report == "data/report.html"
    assert args.max_pages == 5
    assert args.show_progress is False


async def test_day7_run_from_args_runs_crawler_and_exports_reports(
    monkeypatch,
    tmp_path,
):
    created_crawlers = []

    class FakeCrawler:
        def __init__(self) -> None:
            self.crawl_from_config_called = False
            self.closed = False
            self.json_report_path = None
            self.html_report_path = None

        @classmethod
        def from_config(cls, filename):
            crawler = cls()
            crawler.config_filename = filename
            created_crawlers.append(crawler)
            return crawler

        async def crawl_from_config(self):
            self.crawl_from_config_called = True

        async def close(self):
            self.closed = True

        def export_to_json(self, filename):
            self.json_report_path = Path(filename)
            self.json_report_path.write_text("{}", encoding="utf-8")

        def export_to_html_report(self, filename):
            self.html_report_path = Path(filename)
            self.html_report_path.write_text("<html></html>", encoding="utf-8")

        def get_stats(self):
            return {
                "total_pages": 1,
                "successful": 1,
                "failed": 0,
            }

    monkeypatch.setattr(cli, "AdvancedCrawler", FakeCrawler)

    json_report = tmp_path / "report.json"
    html_report = tmp_path / "report.html"

    args = cli.parse_args(
        [
            "config/day7_config.json",
            "--json-report",
            str(json_report),
            "--html-report",
            str(html_report),
        ]
    )

    stats = await cli.run_from_args(args)

    assert stats == {
        "total_pages": 1,
        "successful": 1,
        "failed": 0,
    }

    crawler = created_crawlers[0]

    assert crawler.config_filename == "config/day7_config.json"
    assert crawler.crawl_from_config_called is True
    assert crawler.closed is True
    assert json_report.exists()
    assert html_report.exists()


async def test_day7_run_from_args_can_override_max_pages(monkeypatch):
    created_crawlers = []

    class FakeCrawler:
        def __init__(self) -> None:
            self.crawl_args = None
            self.closed = False

        @classmethod
        def from_config(cls, filename):
            crawler = cls()
            created_crawlers.append(crawler)
            return crawler

        async def collect_start_urls(self):
            return [
                "https://example.com/page-1",
                "https://example.com/page-2",
            ]

        async def crawl(self, urls, *, max_pages, show_progress):
            self.crawl_args = {
                "urls": urls,
                "max_pages": max_pages,
                "show_progress": show_progress,
            }

        async def close(self):
            self.closed = True

        def get_stats(self):
            return {
                "total_pages": 2,
                "successful": 2,
                "failed": 0,
            }

    monkeypatch.setattr(cli, "AdvancedCrawler", FakeCrawler)

    args = cli.parse_args(
        [
            "config/day7_config.json",
            "--max-pages",
            "1",
            "--no-progress",
        ]
    )

    stats = await cli.run_from_args(args)

    crawler = created_crawlers[0]

    assert crawler.crawl_args == {
        "urls": [
            "https://example.com/page-1",
            "https://example.com/page-2",
        ],
        "max_pages": 1,
        "show_progress": False,
    }
    assert crawler.closed is True
    assert stats["total_pages"] == 2


def test_day7_cli_parser_accepts_config_flag():
    args = cli.parse_args(
        [
            "--config",
            "config/day7_config.json",
            "--json-report",
            "data/report.json",
            "--html-report",
            "data/report.html",
            "--max-pages",
            "5",
            "--no-progress",
        ]
    )

    assert args.config is None
    assert args.config_file == "config/day7_config.json"
    assert args.json_report == "data/report.json"
    assert args.html_report == "data/report.html"
    assert args.max_pages == 5
    assert args.show_progress is False
