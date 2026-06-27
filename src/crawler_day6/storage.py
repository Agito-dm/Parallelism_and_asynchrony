import asyncio
import csv
import io
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
import aiofiles


STORAGE_FIELDS = (
    "url",
    "title",
    "text",
    "links",
    "metadata",
    "crawled_at",
    "status_code",
    "content_type",
)


def normalize_crawled_at(value: Any) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()

    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return value.isoformat()

    return str(value)


def normalize_storage_data(data: dict) -> dict[str, Any]:
    normalized = {
        "url": data.get("url", ""),
        "title": data.get("title", ""),
        "text": data.get("text", ""),
        "links": data.get("links") or [],
        "metadata": data.get("metadata") or {},
        "crawled_at": normalize_crawled_at(data.get("crawled_at")),
        "status_code": data.get("status_code"),
        "content_type": data.get("content_type", "text/html"),
    }

    return normalized


class DataStorage(ABC):
    @abstractmethod
    async def save(self, data: dict) -> None:
        """Сохранить одну запись."""

    async def save_many(self, items: Iterable[dict]) -> None:
        """Сохранить несколько записей.

        Базовая реализация сохраняет записи по одной.
        Конкретные storage-классы могут переопределить метод
        для batch-сохранения.
        """
        for item in items:
            await self.save(item)

    async def close(self) -> None:
        """Закрыть ресурсы storage."""
        return None


class JSONStorage(DataStorage):
    def __init__(
        self,
        filename: str | Path,
        *,
        encoding: str = "utf-8",
        indent: int | None = None,
    ) -> None:
        self.filename = Path(filename)
        self.encoding = encoding
        self.indent = indent
        self._lock = asyncio.Lock()

    async def save(self, data: dict) -> None:
        normalized_data = normalize_storage_data(data)

        self.filename.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            normalized_data,
            ensure_ascii=False,
            indent=self.indent,
        )

        async with self._lock:
            async with aiofiles.open(
                self.filename,
                mode="a",
                encoding=self.encoding,
            ) as file:
                await file.write(serialized)
                await file.write("\n")


class CSVStorage(DataStorage):
    def __init__(
        self,
        filename: str | Path,
        *,
        encoding: str = "utf-8",
        fieldnames: list[str] | None = None,
    ) -> None:
        self.filename = Path(filename)
        self.encoding = encoding
        self.fieldnames = fieldnames or list(STORAGE_FIELDS)
        self._lock = asyncio.Lock()
        self._header_written = (
            self.filename.exists()
            and self.filename.stat().st_size > 0
        )
    
    def _prepare_row(self, data: dict) -> dict[str, Any]:
        normalized_data = normalize_storage_data(data)

        row = dict(normalized_data)
        row["links"] = json.dumps(
            row["links"],
            ensure_ascii=False,
        )
        row["metadata"] = json.dumps(
            row["metadata"],
            ensure_ascii=False,
        )

        return row
    
    def _render_csv_row(self, row: dict[str, Any], *, include_header: bool) -> str:
        buffer = io.StringIO()

        writer = csv.DictWriter(
            buffer,
            fieldnames=self.fieldnames,
            extrasaction="ignore",
        )

        if include_header:
            writer.writeheader()

        writer.writerow(row)

        return buffer.getvalue()

    async def save(self, data: dict) -> None:
        row = self._prepare_row(data)

        self.filename.parent.mkdir(parents=True, exist_ok=True)

        async with self._lock:
            include_header = not self._header_written

            csv_content = self._render_csv_row(
                row,
                include_header=include_header,
            )

            async with aiofiles.open(
                self.filename,
                mode="a",
                encoding=self.encoding,
                newline="",
            ) as file:
                await file.write(csv_content)

            self._header_written = True


class SQLiteStorage(DataStorage):
    def __init__(
        self,
        filename: str | Path,
        *,
        batch_size: int = 50,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self.filename = Path(filename)
        self.batch_size = batch_size
        self._connection: aiosqlite.Connection | None = None
        self._buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def init_db(self) -> None:
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        if self._connection is None:
            self._connection = await aiosqlite.connect(self.filename)

        await self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT,
                text TEXT,
                links TEXT,
                metadata TEXT,
                crawled_at TEXT,
                status_code INTEGER,
                content_type TEXT
            )
            """
        )
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pages_crawled_at
            ON pages(crawled_at)
            """
        )
        await self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_pages_status_code
            ON pages(status_code)
            """
        )
        await self._connection.commit()

    async def _get_connection(self) -> aiosqlite.Connection:
        if self._connection is None:
            await self.init_db()

        assert self._connection is not None
        return self._connection

    def _prepare_row(self, data: dict) -> dict[str, Any]:
        normalized_data = normalize_storage_data(data)

        row = dict(normalized_data)
        row["links"] = json.dumps(
            row["links"],
            ensure_ascii=False,
        )
        row["metadata"] = json.dumps(
            row["metadata"],
            ensure_ascii=False,
        )

        return row

    async def save(self, data: dict) -> None:
        row = self._prepare_row(data)

        async with self._lock:
            self._buffer.append(row)

            if len(self._buffer) >= self.batch_size:
                await self._flush_locked()

    async def save_many(self, items: Iterable[dict]) -> None:
        async with self._lock:
            for item in items:
                row = self._prepare_row(item)
                self._buffer.append(row)

            if len(self._buffer) >= self.batch_size:
                await self._flush_locked()

    async def _flush_locked(self) -> None:
        if not self._buffer:
            return

        connection = await self._get_connection()

        rows = [
            (
                row["url"],
                row["title"],
                row["text"],
                row["links"],
                row["metadata"],
                row["crawled_at"],
                row["status_code"],
                row["content_type"],
            )
            for row in self._buffer
        ]

        await connection.executemany(
            """
            INSERT OR REPLACE INTO pages (
                url,
                title,
                text,
                links,
                metadata,
                crawled_at,
                status_code,
                content_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        await connection.commit()

        self._buffer.clear()

    async def flush(self) -> None:
        async with self._lock:
            await self._flush_locked()

    async def close(self) -> None:
        await self.flush()

        if self._connection is not None:
            await self._connection.close()
            self._connection = None
