import asyncio
import json

from crawler_day6.storage import JSONStorage, STORAGE_FIELDS


def read_jsonl(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


async def test_day6_json_storage_saves_single_record(tmp_path):
    output_path = tmp_path / "results.jsonl"
    storage = JSONStorage(output_path)

    await storage.save(
        {
            "url": "https://example.com",
            "title": "Example",
            "text": "Hello",
            "links": ["https://example.com/about"],
            "metadata": {"source": "test"},
            "status_code": 200,
        }
    )

    records = read_jsonl(output_path)

    assert len(records) == 1

    record = records[0]

    assert tuple(record.keys()) == STORAGE_FIELDS
    assert record["url"] == "https://example.com"
    assert record["title"] == "Example"
    assert record["text"] == "Hello"
    assert record["links"] == ["https://example.com/about"]
    assert record["metadata"] == {"source": "test"}
    assert record["status_code"] == 200
    assert record["content_type"] == "text/html"
    assert isinstance(record["crawled_at"], str)


async def test_day6_json_storage_saves_many_records(tmp_path):
    output_path = tmp_path / "results.jsonl"
    storage = JSONStorage(output_path)

    await storage.save_many(
        [
            {
                "url": "https://example.com/1",
                "title": "Page 1",
            },
            {
                "url": "https://example.com/2",
                "title": "Page 2",
            },
        ]
    )

    records = read_jsonl(output_path)

    assert len(records) == 2
    assert records[0]["url"] == "https://example.com/1"
    assert records[0]["title"] == "Page 1"
    assert records[1]["url"] == "https://example.com/2"
    assert records[1]["title"] == "Page 2"


async def test_day6_json_storage_preserves_unicode_text(tmp_path):
    output_path = tmp_path / "results.jsonl"
    storage = JSONStorage(output_path)

    await storage.save(
        {
            "url": "https://example.com/ru",
            "title": "Тестовая страница",
            "text": "Повреждение дорожного покрытия: выбоина",
            "links": [],
            "metadata": {"language": "ru"},
        }
    )

    file_content = output_path.read_text(encoding="utf-8")

    assert "Тестовая страница" in file_content
    assert "выбоина" in file_content

    records = read_jsonl(output_path)

    assert records[0]["title"] == "Тестовая страница"
    assert records[0]["text"] == "Повреждение дорожного покрытия: выбоина"


async def test_day6_json_storage_creates_parent_directories(tmp_path):
    output_path = tmp_path / "nested" / "folder" / "results.jsonl"
    storage = JSONStorage(output_path)

    await storage.save(
        {
            "url": "https://example.com",
            "title": "Example",
        }
    )

    assert output_path.exists()

    records = read_jsonl(output_path)

    assert len(records) == 1
    assert records[0]["url"] == "https://example.com"


async def test_day6_json_storage_handles_concurrent_saves(tmp_path):
    output_path = tmp_path / "results.jsonl"
    storage = JSONStorage(output_path)

    async def save_item(index: int) -> None:
        await storage.save(
            {
                "url": f"https://example.com/{index}",
                "title": f"Page {index}",
            }
        )

    await asyncio.gather(
        *[save_item(index) for index in range(20)]
    )

    records = read_jsonl(output_path)

    assert len(records) == 20

    indexes = sorted(
        int(record["url"].rsplit("/", maxsplit=1)[-1])
        for record in records
    )

    assert indexes == list(range(20))
