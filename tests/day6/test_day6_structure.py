import pytest

from crawler_day5.crawler import AsyncCrawler as Day5AsyncCrawler
from crawler_day6.crawler import AsyncCrawler
from crawler_day6.storage import (
    CSVStorage,
    DataStorage,
    JSONStorage,
    SQLiteStorage,
    STORAGE_FIELDS,
    normalize_storage_data,
)


class MemoryStorage(DataStorage):
    def __init__(self) -> None:
        self.items = []
        self.closed = False

    async def save(self, data: dict) -> None:
        self.items.append(data)

    async def close(self) -> None:
        self.closed = True


def test_day6_data_storage_is_abstract():
    with pytest.raises(TypeError):
        DataStorage()


async def test_day6_data_storage_save_many_uses_save():
    storage = MemoryStorage()

    await storage.save_many(
        [
            {"url": "https://example.com/1"},
            {"url": "https://example.com/2"},
        ]
    )

    assert storage.items == [
        {"url": "https://example.com/1"},
        {"url": "https://example.com/2"},
    ]


def test_day6_storage_classes_can_be_created(tmp_path):
    json_storage = JSONStorage(tmp_path / "results.jsonl")
    csv_storage = CSVStorage(tmp_path / "results.csv")
    sqlite_storage = SQLiteStorage(tmp_path / "results.db")

    assert json_storage.filename == tmp_path / "results.jsonl"
    assert csv_storage.filename == tmp_path / "results.csv"
    assert sqlite_storage.filename == tmp_path / "results.db"


def test_day6_sqlite_storage_rejects_invalid_batch_size(tmp_path):
    with pytest.raises(ValueError):
        SQLiteStorage(tmp_path / "results.db", batch_size=0)


def test_day6_crawler_extends_day5_crawler():
    crawler = AsyncCrawler()

    assert isinstance(crawler, AsyncCrawler)
    assert isinstance(crawler, Day5AsyncCrawler)
    assert crawler.storage is None
    assert crawler.get_storage_stats() == {
        "saved": 0,
        "save_errors": 0,
        "failed_saves": 0,
    }


def test_day6_crawler_rejects_invalid_storage_settings():
    with pytest.raises(ValueError):
        AsyncCrawler(storage_save_retries=-1)

    with pytest.raises(ValueError):
        AsyncCrawler(storage_retry_delay=-0.1)


async def test_day6_crawler_closes_storage():
    storage = MemoryStorage()
    crawler = AsyncCrawler(storage=storage)

    await crawler.close()

    assert storage.closed is True


def test_day6_normalize_storage_data_fills_standard_fields():
    data = normalize_storage_data(
        {
            "url": "https://example.com",
            "title": "Example",
            "text": "Пример текста",
            "links": ["https://example.com/about"],
            "metadata": {"source": "test"},
            "status_code": 200,
        }
    )

    assert tuple(data.keys()) == STORAGE_FIELDS
    assert data["url"] == "https://example.com"
    assert data["title"] == "Example"
    assert data["text"] == "Пример текста"
    assert data["links"] == ["https://example.com/about"]
    assert data["metadata"] == {"source": "test"}
    assert data["status_code"] == 200
    assert data["content_type"] == "text/html"
    assert isinstance(data["crawled_at"], str)
