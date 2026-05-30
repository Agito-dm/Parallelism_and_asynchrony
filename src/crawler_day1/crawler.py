import asyncio
import logging

import aiohttp


logger = logging.getLogger(__name__)


class AsyncCrawler:
    def __init__(
        self,
        max_concurrent: int = 10,
        connect_timeout: float = 5.0,
        read_timeout: float = 10.0,
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")

        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)

        self._timeout = aiohttp.ClientTimeout(
            connect=connect_timeout,
            sock_read=read_timeout,
        )

        self._session: aiohttp.ClientSession | None = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.max_concurrent)

            self._session = aiohttp.ClientSession(
                timeout=self._timeout,
                connector=connector,
            )

        return self._session
    
    async def fetch_url(self, url: str) -> str:
        async with self._semaphore:
            logger.info("Start loading URL: %s", url)

            try:
                session = await self._get_session()

                async with session.get(url) as response:
                    response.raise_for_status()

                    text = await response.text()

                    logger.info(
                        "Successfully loaded URL: %s | status=%s | bytes=%s",
                        url,
                        response.status,
                        len(text),
                    )

                    return text

            except aiohttp.ClientResponseError as error:
                logger.warning(
                    "HTTP error while loading URL: %s | status=%s | message=%s",
                    url,
                    error.status,
                    error.message,
                )

            except asyncio.TimeoutError:
                logger.warning("Timeout while loading URL: %s", url)

            except aiohttp.ClientError as error:
                logger.warning(
                    "Network error while loading URL: %s | error=%s",
                    url,
                    type(error).__name__,
                )

            return ""
    
    async def fetch_urls(self, urls: list[str]) -> dict[str, str]:
        tasks = [asyncio.create_task(self.fetch_url(url)) for url in urls]
        pages = await asyncio.gather(*tasks)

        return dict(zip(urls, pages))

    async def close(self) -> None:
        if self._session is not None and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "AsyncCrawler":
        await self._get_session()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback) -> None:
        await self.close()
    