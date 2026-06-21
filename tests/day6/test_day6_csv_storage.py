import asyncio
import csv
import json

from crawler_day6.storage import CSVStorage, STORAGE_FIELDS


def read_csv(path, encoding="utf-8"):
    with path.open("r", encoding=encoding, newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


async def test_day6_csv_storage_saves_single_record(tmp_path):
    output_path = tmp_path / "results.csv"
    storage = CSVStorage(output_path)

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

    rows = read_csv(output_path)

    assert len(rows) == 1

    row = rows[0]

    assert tuple(row.keys()) == STORAGE_FIELDS
    assert row["url"] == "https://example.com"
    assert row["title"] == "Example"
    assert row["text"] == "Hello"
    assert json.loads(row["links"]) == ["https://example.com/about"]
    assert json.loads(row["metadata"]) == {"source": "test"}
    assert row["status_code"] == "200"
    assert row["content_type"] == "text/html"
    assert isinstance(row["crawled_at"], str)


async def test_day6_csv_storage_saves_many_records_without_duplicate_header(tmp_path):
    output_path = tmp_path / "results.csv"
    storage = CSVStorage(output_path)

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

    file_lines = output_path.read_text(encoding="utf-8").splitlines()

    assert file_lines[0].startswith("url,title,text,links,metadata")
    assert sum(1 for line in file_lines if line.startswith("url,title")) == 1

    rows = read_csv(output_path)

    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/1"
    assert rows[0]["title"] == "Page 1"
    assert rows[1]["url"] == "https://example.com/2"
    assert rows[1]["title"] == "Page 2"


async def test_day6_csv_storage_handles_special_characters(tmp_path):
    output_path = tmp_path / "results.csv"
    storage = CSVStorage(output_path)

    text = 'Текст с запятой, кавычками "пример" и переносом\nстроки'

    await storage.save(
        {
            "url": "https://example.com/special",
            "title": 'Страница "Тест", версия 1',
            "text": text,
            "links": [
                "https://example.com/a,b",
                "https://example.com/quote",
            ],
            "metadata": {
                "language": "ru",
                "note": 'значение с "кавычками"',
            },
            "status_code": 200,
        }
    )

    rows = read_csv(output_path)

    assert len(rows) == 1

    row = rows[0]

    assert row["title"] == 'Страница "Тест", версия 1'
    assert row["text"] == text
    assert json.loads(row["links"]) == [
        "https://example.com/a,b",
        "https://example.com/quote",
    ]
    assert json.loads(row["metadata"]) == {
        "language": "ru",
        "note": 'значение с "кавычками"',
    }


async def test_day6_csv_storage_creates_parent_directories(tmp_path):
    output_path = tmp_path / "nested" / "folder" / "results.csv"
    storage = CSVStorage(output_path)

    await storage.save(
        {
            "url": "https://example.com",
            "title": "Example",
        }
    )

    assert output_path.exists()

    rows = read_csv(output_path)

    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.com"


async def test_day6_csv_storage_supports_custom_encoding(tmp_path):
    output_path = tmp_path / "results_cp1251.csv"
    storage = CSVStorage(output_path, encoding="cp1251")

    await storage.save(
        {
            "url": "https://example.com/ru",
            "title": "Русская страница",
            "text": "Текст на русском языке",
        }
    )

    rows = read_csv(output_path, encoding="cp1251")

    assert len(rows) == 1
    assert rows[0]["title"] == "Русская страница"
    assert rows[0]["text"] == "Текст на русском языке"


async def test_day6_csv_storage_handles_concurrent_saves(tmp_path):
    output_path = tmp_path / "results.csv"
    storage = CSVStorage(output_path)

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

    rows = read_csv(output_path)

    assert len(rows) == 20

    indexes = sorted(
        int(row["url"].rsplit("/", maxsplit=1)[-1])
        for row in rows
    )

    assert indexes == list(range(20))

    file_lines = output_path.read_text(encoding="utf-8").splitlines()

    assert sum(1 for line in file_lines if line.startswith("url,title")) == 1
