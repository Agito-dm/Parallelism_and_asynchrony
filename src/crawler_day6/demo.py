import asyncio
import csv
import json
from pathlib import Path

import aiosqlite

from crawler_day6.crawler import AsyncCrawler
from crawler_day6.storage import CSVStorage, JSONStorage, SQLiteStorage


OUTPUT_DIR = Path("data/day6_demo")


class FakeResponse:
    def __init__(
        self,
        html: str,
        *,
        status: int = 200,
        headers: dict | None = None,
    ) -> None:
        self.html = html
        self.status = status
        self.headers = headers or {"Content-Type": "text/html"}

    async def text(self) -> str:
        return self.html

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None


class FakeSession:
    def __init__(self) -> None:
        main_response = FakeResponse(
            """
            <html>
                <head>
                    <title>Main page</title>
                    <meta name="description" content="Demo crawler page">
                </head>
                <body>
                    <h1>Main page</h1>
                    <p>Hello from async crawler demo.</p>
                    <a href="https://example.com/about">About</a>
                </body>
            </html>
            """
        )

        about_response = FakeResponse(
            """
            <html>
                <head>
                    <title>About page</title>
                </head>
                <body>
                    <h1>About</h1>
                    <p>This page is used to demonstrate async storage.</p>
                </body>
            </html>
            """
        )

        self.responses = {
            "https://example.com": main_response,
            "https://example.com/": main_response,
            "https://example.com/about": about_response,
        }

    def get(self, url: str, **kwargs):
        return self.responses[url]


def create_demo_crawler(storage):
    session = FakeSession()

    crawler = AsyncCrawler(
        storage=storage,
        respect_robots=False,
        requests_per_second=1000,
        max_concurrent=5,
    )

    async def fake_get_session():
        return session

    crawler._get_session = fake_get_session

    return crawler


async def run_crawler_with_storage(storage, name: str) -> None:
    crawler = create_demo_crawler(storage)

    await crawler.crawl(
        [
            "https://example.com",
            "https://example.com/about",
        ],
        max_pages=2,
    )

    print(f"\n{name}")
    print("-" * len(name))
    print("Storage stats:", crawler.get_storage_stats())

    await crawler.close()


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []

    records = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))

    return records


def read_csv_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


async def read_sqlite_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []

    async with aiosqlite.connect(path) as connection:
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


async def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "results.jsonl"
    csv_path = OUTPUT_DIR / "results.csv"
    sqlite_path = OUTPUT_DIR / "crawler.db"

    for path in [json_path, csv_path, sqlite_path]:
        if path.exists():
            path.unlink()

    await run_crawler_with_storage(
        JSONStorage(json_path),
        "JSONStorage demo",
    )

    await run_crawler_with_storage(
        CSVStorage(csv_path),
        "CSVStorage demo",
    )

    await run_crawler_with_storage(
        SQLiteStorage(sqlite_path, batch_size=2),
        "SQLiteStorage demo",
    )

    json_records = read_jsonl(json_path)
    csv_records = read_csv_rows(csv_path)
    sqlite_records = await read_sqlite_rows(sqlite_path)

    print("\nSaved files")
    print("-----------")
    print("JSONL:", json_path)
    print("CSV:  ", csv_path)
    print("DB:   ", sqlite_path)

    print("\nRead back statistics")
    print("--------------------")
    print("JSONL records: ", len(json_records))
    print("CSV records:   ", len(csv_records))
    print("SQLite records:", len(sqlite_records))

    if json_records:
        print("\nExample JSONL record:")
        print(json.dumps(json_records[0], ensure_ascii=False, indent=2))

    if csv_records:
        print("\nExample CSV record:")
        print(json.dumps(csv_records[0], ensure_ascii=False, indent=2))

    if sqlite_records:
        print("\nExample SQLite record:")
        print(json.dumps(sqlite_records[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
