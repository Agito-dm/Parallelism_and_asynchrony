import heapq


class CrawlerQueue:
    def __init__(self) -> None:
        self._queue: list[tuple[int, int, str]] = []
        self._queued_urls: set[str] = set()
        self._processed_urls: set[str] = set()
        self._failed_urls: dict[str, str] = {}
        self._url_depths: dict[str, int] = {}
        self._counter = 0

    def add_url(self, url: str, priority: int = 0, depth: int = 0) -> bool:
        if not url:
            return False

        if url in self._queued_urls:
            return False

        if url in self._processed_urls:
            return False

        if url in self._failed_urls:
            return False

        heapq.heappush(self._queue, (-priority, self._counter, url))
        self._queued_urls.add(url)
        self._url_depths[url] = depth
        self._counter += 1

        return True

    async def get_next(self) -> str | None:
        while self._queue:
            _priority, _counter, url = heapq.heappop(self._queue)

            if url not in self._queued_urls:
                continue

            if url in self._processed_urls:
                self._queued_urls.discard(url)
                continue

            if url in self._failed_urls:
                self._queued_urls.discard(url)
                continue

            self._queued_urls.remove(url)
            return url

        return None

    def mark_processed(self, url: str) -> None:
        self._queued_urls.discard(url)
        self._processed_urls.add(url)

    def mark_failed(self, url: str, error: str) -> None:
        self._queued_urls.discard(url)
        self._failed_urls[url] = error

    def get_depth(self, url: str) -> int:
        return self._url_depths.get(url, 0)

    def get_stats(self) -> dict:
        return {
            "queued": len(self._queued_urls),
            "processed": len(self._processed_urls),
            "failed": len(self._failed_urls),
            "total_known": (
                len(self._queued_urls)
                + len(self._processed_urls)
                + len(self._failed_urls)
            ),
        }
