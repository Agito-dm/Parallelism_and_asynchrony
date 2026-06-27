import json

from crawler_day7.crawler import AdvancedCrawler
from crawler_day7.reporting import (
    export_stats_to_html,
    export_stats_to_json,
    render_stats_html,
)


def make_stats() -> dict:
    return {
        "total_pages": 3,
        "successful": 2,
        "failed": 1,
        "status_codes": {
            "200": 2,
            "404": 1,
        },
        "top_domains": {
            "example.com": 3,
        },
        "started_at": "2026-06-21T10:00:00+00:00",
        "finished_at": "2026-06-21T10:00:02+00:00",
        "duration_seconds": 2.0,
        "pages_per_second": 1.5,
    }


def test_day7_export_stats_to_json_creates_readable_report(tmp_path):
    output_path = tmp_path / "reports" / "stats.json"

    export_stats_to_json(make_stats(), output_path)

    assert output_path.exists()

    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["total_pages"] == 3
    assert data["successful"] == 2
    assert data["failed"] == 1
    assert data["status_codes"] == {
        "200": 2,
        "404": 1,
    }
    assert data["top_domains"] == {
        "example.com": 3,
    }


def test_day7_render_stats_html_contains_summary_tables():
    html = render_stats_html(make_stats())

    assert "<!DOCTYPE html>" in html
    assert "Crawler Report" in html
    assert "Total pages" in html
    assert "Successful" in html
    assert "Failed" in html
    assert "Status codes" in html
    assert "Top domains" in html
    assert "200" in html
    assert "404" in html
    assert "example.com" in html


def test_day7_render_stats_html_escapes_values():
    stats = make_stats()
    stats["top_domains"] = {
        "<script>alert(1)</script>": 1,
    }

    html = render_stats_html(stats)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_day7_export_stats_to_html_creates_report_file(tmp_path):
    output_path = tmp_path / "reports" / "stats.html"

    export_stats_to_html(make_stats(), output_path)

    assert output_path.exists()

    html = output_path.read_text(encoding="utf-8")

    assert "<html" in html
    assert "Crawler Report" in html
    assert "example.com" in html


async def test_day7_advanced_crawler_exports_current_stats(tmp_path):
    crawler = AdvancedCrawler(
        respect_robots=False,
        requests_per_second=1000,
    )

    crawler.advanced_stats.record_success(
        "https://example.com/page-1",
        status_code=200,
    )
    crawler.advanced_stats.record_failure(
        "https://example.com/missing",
        status_code=404,
    )
    crawler.advanced_stats.finish()

    json_path = tmp_path / "crawler-stats.json"
    html_path = tmp_path / "crawler-stats.html"

    crawler.export_to_json(json_path)
    crawler.export_to_html_report(html_path)

    json_data = json.loads(json_path.read_text(encoding="utf-8"))
    html = html_path.read_text(encoding="utf-8")

    assert json_data["total_pages"] == 2
    assert json_data["successful"] == 1
    assert json_data["failed"] == 1
    assert json_data["status_codes"] == {
        "200": 1,
        "404": 1,
    }

    assert "Crawler Report" in html
    assert "example.com" in html
    assert "404" in html

    await crawler.close()
