import asyncio
from time import perf_counter


class RateLimiter:
    def __init__(
        self,
        requests_per_second: float = 1.0,
        per_domain: bool = True,
    ) -> None:
        if requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")

        self.requests_per_second = requests_per_second
        self.per_domain = per_domain
        self.min_interval = 1.0 / requests_per_second

        self._last_request_times: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_key(self, domain: str | None = None) -> str:
        if self.per_domain:
            return domain or "__default__"

        return "__global__"

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        return self._locks[key]

    async def acquire(self, domain: str | None = None) -> None:
        key = self._get_key(domain)
        lock = self._get_lock(key)

        async with lock:
            now = perf_counter()
            last_request_time = self._last_request_times.get(key)

            if last_request_time is not None:
                elapsed = now - last_request_time
                wait_time = self.min_interval - elapsed

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

            self._last_request_times[key] = perf_counter()

    def reset(self) -> None:
        self._last_request_times.clear()
        self._locks.clear()
