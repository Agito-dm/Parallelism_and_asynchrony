import asyncio
import logging
from typing import Any

from crawler_day5.crawler import AsyncCrawler as BaseAsyncCrawler

from crawler_day6.storage import DataStorage, normalize_storage_data

logger = logging.getLogger(__name__)


class AsyncCrawler(BaseAsyncCrawler):
    def __init__(
        self,
        *args,
        storage: DataStorage | None = None,
        storage_save_retries: int = 2,
        storage_retry_delay: float = 0.1,
        **kwargs,
    ) -> None:
        if storage_save_retries < 0:
            raise ValueError("storage_save_retries must be non-negative")

        if storage_retry_delay < 0:
            raise ValueError("storage_retry_delay must be non-negative")

        super().__init__(*args, **kwargs)

        self.storage = storage
        self.storage_save_retries = storage_save_retries
        self.storage_retry_delay = storage_retry_delay

        self.storage_stats = {
            "saved": 0,
            "save_errors": 0,
            "failed_saves": 0,
        }

    def get_storage_stats(self) -> dict:
        return dict(self.storage_stats)

    def _is_page_data_successful(self, page_data: Any) -> bool:
        if not isinstance(page_data, dict):
            return False

        if not page_data:
            return False

        if page_data.get("error"):
            return False

        if page_data.get("errors"):
            return False

        return True

    def _build_storage_data(self, url: str, page_data: dict) -> dict:
        storage_data = {
            "url": page_data.get("url") or url,
            "title": page_data.get("title", ""),
            "text": page_data.get("text", ""),
            "links": page_data.get("links") or [],
            "metadata": page_data.get("metadata") or {},
            "crawled_at": page_data.get("crawled_at"),
            "status_code": page_data.get("status_code", 200),
            "content_type": page_data.get("content_type", "text/html"),
        }

        return normalize_storage_data(storage_data)

    async def _save_with_retries(self, data: dict) -> bool:
        if self.storage is None:
            return False

        for attempt in range(self.storage_save_retries + 1):
            try:
                await self.storage.save(data)
            except Exception as error:
                self.storage_stats["save_errors"] += 1

                logger.warning(
                    "Storage save failed | attempt=%s | error=%s",
                    attempt + 1,
                    error,
                )

                if attempt >= self.storage_save_retries:
                    self.storage_stats["failed_saves"] += 1
                    logger.error(
                        "Storage save failed permanently | url=%s | attempts=%s",
                        data.get("url"),
                        attempt + 1,
                    )
                    return False

                if self.storage_retry_delay > 0:
                    await asyncio.sleep(self.storage_retry_delay)
            else:
                self.storage_stats["saved"] += 1
                return True

        return False

    async def _save_page_data(self, url: str, page_data: dict) -> bool:
        if self.storage is None:
            return False

        storage_data = self._build_storage_data(url, page_data)

        return await self._save_with_retries(storage_data)

    async def fetch_and_parse(self, url: str) -> dict | None:
        page_data = await super().fetch_and_parse(url)

        if self.storage is not None and self._is_page_data_successful(page_data):
            await self._save_page_data(url, page_data)

        return page_data

    async def close(self) -> None:
        await super().close()

        if self.storage is not None:
            await self.storage.close()
