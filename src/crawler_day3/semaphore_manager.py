import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlparse


class SemaphoreManager:
    def __init__(self, max_global: int = 10, max_per_domain: int = 2) -> None:
        if max_global < 1:
            raise ValueError("max_global must be at least 1")

        if max_per_domain < 1:
            raise ValueError("max_per_domain must be at least 1")

        self.max_global = max_global
        self.max_per_domain = max_per_domain

        self._global_semaphore = asyncio.Semaphore(max_global)
        self._domain_semaphores: dict[str, asyncio.Semaphore] = {}

        self.active_total = 0
        self.active_by_domain: dict[str, int] = {}

    @asynccontextmanager
    async def limit_for(self, url: str) -> AsyncIterator[None]:
        domain = self._get_domain(url)
        domain_semaphore = self._get_domain_semaphore(domain)

        async with domain_semaphore:
            async with self._global_semaphore:
                self._increment_active(domain)

                try:
                    yield
                finally:
                    self._decrement_active(domain)

    def get_stats(self) -> dict:
        return {
            "max_global": self.max_global,
            "max_per_domain": self.max_per_domain,
            "active_total": self.active_total,
            "active_by_domain": dict(self.active_by_domain),
        }

    def _get_domain(self, url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if not domain:
            return "unknown"

        return domain

    def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(
                self.max_per_domain
            )

        return self._domain_semaphores[domain]

    def _increment_active(self, domain: str) -> None:
        self.active_total += 1
        self.active_by_domain[domain] = self.active_by_domain.get(domain, 0) + 1

    def _decrement_active(self, domain: str) -> None:
        self.active_total -= 1

        current_domain_active = self.active_by_domain.get(domain, 0)

        if current_domain_active <= 1:
            self.active_by_domain.pop(domain, None)
        else:
            self.active_by_domain[domain] = current_domain_active - 1
