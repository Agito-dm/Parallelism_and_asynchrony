import json
from datetime import datetime, timezone

from crawler_day6.crawler import AsyncCrawler
from crawler_day6.storage import DataStorage, JSONStorage, normalize_storage_data


class MemoryStorage(DataStorage):
    def __init__(self) -> None:
        self.items = []

    async def save(self, data: dict) -> None:
        self.items.append(data)


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
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def get(self, url: str, **kwargs):
        return self.response


def make_crawler(storage, session):
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


def test_day6_normalize_storage_data_converts_datetime_to_iso_string():
    crawled_at = datetime(2026, 6, 21, 5, 30, tzinfo=timezone.utc)

    data = normalize_storage_data(
        {
            "url": "https://example.com",
            "crawled_at": crawled_at,
        }
    )

    assert data["crawled_at"] == "2026-06-21T05:30:00+00:00"


async def test_day6_json_storage_accepts_datetime_crawled_at(tmp_path):
    output_path = tmp_path / "results.jsonl"
    storage = JSONStorage(output_path)

    crawled_at = datetime(2026, 6, 21, 5, 30, tzinfo=timezone.utc)

    await storage.save(
        {
            "url": "https://example.com",
            "title": "Datetime test",
            "crawled_at": crawled_at,
        }
    )

    line = output_path.read_text(encoding="utf-8").strip()
    record = json.loads(line)

    assert record["crawled_at"] == "2026-06-21T05:30:00+00:00"


async def test_day6_storage_preserves_real_status_code_and_content_type():
    storage = MemoryStorage()
    session = FakeSession(
        FakeResponse(
            """
            <html>
                <head><title>Created page</title></head>
                <body>Created content</body>
            </html>
            """,
            status=201,
            headers={"Content-Type": "application/xhtml+xml; charset=utf-8"},
        )
    )
    crawler = make_crawler(storage=storage, session=session)

    page_data = await crawler.fetch_and_parse("https://example.com/created")

    assert page_data is not None
    assert len(storage.items) == 1

    saved = storage.items[0]

    assert saved["url"] == "https://example.com/created"
    assert saved["status_code"] == 201
    assert saved["content_type"] == "application/xhtml+xml; charset=utf-8"

    await crawler.close()