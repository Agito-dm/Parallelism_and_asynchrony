import json

import pytest

from crawler_day6.storage import CSVStorage, JSONStorage, SQLiteStorage
from crawler_day7.config import CrawlerConfig, load_config
from crawler_day7.crawler import AdvancedCrawler, create_storage_from_config


def test_day7_load_config_from_json_file(tmp_path):
    config_path = tmp_path / "config.json"

    config_path.write_text(
        json.dumps(
            {
                "start_urls": ["https://example.com"],
                "sitemap_urls": ["https://example.com/sitemap.xml"],
                "max_pages": 25,
                "max_depth": 3,
                "max_concurrent": 7,
                "rate_limit": 2.5,
                "respect_robots": False,
                "include_patterns": ["/blog"],
                "exclude_patterns": ["/admin"],
                "output": {
                    "type": "csv",
                    "filename": str(tmp_path / "results.csv"),
                },
                "logging": {
                    "level": "DEBUG",
                    "filename": str(tmp_path / "crawler.log"),
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.start_urls == ["https://example.com"]
    assert config.sitemap_urls == ["https://example.com/sitemap.xml"]
    assert config.max_pages == 25
    assert config.max_depth == 3
    assert config.max_concurrent == 7
    assert config.rate_limit == 2.5
    assert config.respect_robots is False
    assert config.include_patterns == ["/blog"]
    assert config.exclude_patterns == ["/admin"]
    assert config.output.type == "csv"
    assert config.logging.level == "DEBUG"


def test_day7_config_uses_defaults_for_missing_values(tmp_path):
    config_path = tmp_path / "config.json"

    config_path.write_text(
        json.dumps(
            {
                "start_urls": ["https://example.com"]
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.start_urls == ["https://example.com"]
    assert config.sitemap_urls == []
    assert config.max_pages == 100
    assert config.max_depth == 2
    assert config.max_concurrent == 5
    assert config.rate_limit == 1.0
    assert config.respect_robots is True
    assert config.output.type == "jsonl"
    assert config.output.filename == "data/day7_results.jsonl"


def test_day7_config_rejects_invalid_output_type():
    with pytest.raises(ValueError, match="output.type"):
        CrawlerConfig.from_dict(
            {
                "output": {
                    "type": "xml",
                    "filename": "data/results.xml",
                }
            }
        )


def test_day7_create_storage_from_config_jsonl(tmp_path):
    config = CrawlerConfig.from_dict(
        {
            "output": {
                "type": "jsonl",
                "filename": str(tmp_path / "results.jsonl"),
            }
        }
    )

    storage = create_storage_from_config(config)

    assert isinstance(storage, JSONStorage)


def test_day7_create_storage_from_config_csv(tmp_path):
    config = CrawlerConfig.from_dict(
        {
            "output": {
                "type": "csv",
                "filename": str(tmp_path / "results.csv"),
            }
        }
    )

    storage = create_storage_from_config(config)

    assert isinstance(storage, CSVStorage)


def test_day7_create_storage_from_config_sqlite(tmp_path):
    config = CrawlerConfig.from_dict(
        {
            "output": {
                "type": "sqlite",
                "filename": str(tmp_path / "crawler.db"),
            }
        }
    )

    storage = create_storage_from_config(config)

    assert isinstance(storage, SQLiteStorage)


async def test_day7_advanced_crawler_can_be_created_from_config(tmp_path):
    config_path = tmp_path / "config.json"

    config_path.write_text(
        json.dumps(
            {
                "start_urls": ["https://example.com"],
                "max_pages": 5,
                "max_depth": 1,
                "max_concurrent": 2,
                "rate_limit": 5.0,
                "respect_robots": False,
                "output": {
                    "type": "jsonl",
                    "filename": str(tmp_path / "results.jsonl"),
                },
                "logging": {
                    "level": "INFO",
                    "filename": str(tmp_path / "crawler.log"),
                },
            }
        ),
        encoding="utf-8",
    )

    crawler = AdvancedCrawler.from_config(config_path)

    assert crawler.config.start_urls == ["https://example.com"]
    assert crawler.config.max_pages == 5
    assert crawler.config.max_depth == 1
    assert crawler.config.max_concurrent == 2
    assert crawler.config.rate_limit == 5.0
    assert crawler.config.respect_robots is False
    assert isinstance(crawler.storage, JSONStorage)

    await crawler.close()
