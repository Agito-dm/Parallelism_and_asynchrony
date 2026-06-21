import json

import aiosqlite

from crawler_day6.storage import SQLiteStorage


async def read_pages(db_path):
    async with aiosqlite.connect(db_path) as connection:
        connection.row_factory = aiosqlite.Row

        cursor = await connection.execute(
            """
            SELECT
                url,
                title,
                text,
                links,
                metadata,
                crawled_at,
                status_code,
                content_type
            FROM pages
            ORDER BY url
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()

    return [dict(row) for row in rows]


async def test_day6_sqlite_storage_init_db_creates_table_and_indexes(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path)

    await storage.init_db()
    await storage.close()

    async with aiosqlite.connect(db_path) as connection:
        cursor = await connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
        tables = {row[0] for row in await cursor.fetchall()}
        await cursor.close()

        cursor = await connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            """
        )
        indexes = {row[0] for row in await cursor.fetchall()}
        await cursor.close()

    assert "pages" in tables
    assert "idx_pages_crawled_at" in indexes
    assert "idx_pages_status_code" in indexes


async def test_day6_sqlite_storage_saves_record_after_flush(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=10)

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

    rows_before_flush = await read_pages(db_path) if db_path.exists() else []
    assert rows_before_flush == []

    await storage.flush()

    rows = await read_pages(db_path)

    assert len(rows) == 1

    row = rows[0]

    assert row["url"] == "https://example.com"
    assert row["title"] == "Example"
    assert row["text"] == "Hello"
    assert json.loads(row["links"]) == ["https://example.com/about"]
    assert json.loads(row["metadata"]) == {"source": "test"}
    assert row["status_code"] == 200
    assert row["content_type"] == "text/html"
    assert isinstance(row["crawled_at"], str)

    await storage.close()


async def test_day6_sqlite_storage_auto_flushes_by_batch_size(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=2)

    await storage.save(
        {
            "url": "https://example.com/1",
            "title": "Page 1",
        }
    )

    assert not db_path.exists()

    await storage.save(
        {
            "url": "https://example.com/2",
            "title": "Page 2",
        }
    )

    rows = await read_pages(db_path)

    assert len(rows) == 2
    assert rows[0]["url"] == "https://example.com/1"
    assert rows[1]["url"] == "https://example.com/2"

    await storage.close()


async def test_day6_sqlite_storage_save_many_uses_batch_insert(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=3)

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
            {
                "url": "https://example.com/3",
                "title": "Page 3",
            },
        ]
    )

    rows = await read_pages(db_path)

    assert len(rows) == 3
    assert [row["url"] for row in rows] == [
        "https://example.com/1",
        "https://example.com/2",
        "https://example.com/3",
    ]

    await storage.close()


async def test_day6_sqlite_storage_close_flushes_remaining_records(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=10)

    await storage.save(
        {
            "url": "https://example.com/not-flushed-yet",
            "title": "Close flush",
        }
    )

    rows_before_close = await read_pages(db_path) if db_path.exists() else []
    assert rows_before_close == []

    await storage.close()

    rows = await read_pages(db_path)

    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.com/not-flushed-yet"


async def test_day6_sqlite_storage_replaces_record_with_same_url(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=1)

    await storage.save(
        {
            "url": "https://example.com/page",
            "title": "Old title",
        }
    )
    await storage.save(
        {
            "url": "https://example.com/page",
            "title": "New title",
        }
    )

    rows = await read_pages(db_path)

    assert len(rows) == 1
    assert rows[0]["url"] == "https://example.com/page"
    assert rows[0]["title"] == "New title"

    await storage.close()


async def test_day6_sqlite_storage_preserves_unicode_and_json_fields(tmp_path):
    db_path = tmp_path / "crawler.db"
    storage = SQLiteStorage(db_path, batch_size=1)

    await storage.save(
        {
            "url": "https://example.com/ru",
            "title": "Русская страница",
            "text": "Текст с описанием повреждения: выбоина",
            "links": ["https://example.com/раздел"],
            "metadata": {
                "language": "ru",
                "note": "проверка Unicode",
            },
            "status_code": 200,
        }
    )

    rows = await read_pages(db_path)

    assert len(rows) == 1

    row = rows[0]

    assert row["title"] == "Русская страница"
    assert row["text"] == "Текст с описанием повреждения: выбоина"
    assert json.loads(row["links"]) == ["https://example.com/раздел"]
    assert json.loads(row["metadata"]) == {
        "language": "ru",
        "note": "проверка Unicode",
    }

    await storage.close()
