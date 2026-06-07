import asyncio
import logging

import aiohttp

from crawler_day4.crawler import AsyncCrawler as BaseAsyncCrawler

from crawler_day5.errors import (
    CrawlerError,
    NetworkError,
    PermanentError,
    TransientError,
)
from crawler_day5.retry_strategy import RetryStrategy

logger = logging.getLogger(__name__)


class AsyncCrawler(BaseAsyncCrawler):
    TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}
    PERMANENT_HTTP_STATUSES = {400, 401, 403, 404, 405, 410}

    def __init__(
        self,
        *args,
        retry_strategy: RetryStrategy | None = None,
        total_timeout: float | None = None,
        timeout_backoff_factor: float = 2.0,
        **kwargs,
    ) -> None:
        if total_timeout is not None and total_timeout <= 0:
            raise ValueError("total_timeout must be positive")

        if timeout_backoff_factor < 1.0:
            raise ValueError("timeout_backoff_factor must be greater than or equal to 1.0")
        super().__init__(*args, **kwargs)

        self.retry_strategy = retry_strategy or RetryStrategy()
        
        self.total_timeout = total_timeout
        self.timeout_backoff_factor = timeout_backoff_factor

        self.error_history: list[dict] = []
        self.permanent_error_urls: dict[str, str] = {}

    def _classify_http_status(self, status: int, url: str) -> CrawlerError | None:
        if status in self.TRANSIENT_HTTP_STATUSES:
            return TransientError(
                f"Transient HTTP error: {status}",
                url=url,
                status_code=status,
            )

        if status >= 500:
            return TransientError(
                f"Server HTTP error: {status}",
                url=url,
                status_code=status,
            )

        if status in self.PERMANENT_HTTP_STATUSES:
            return PermanentError(
                f"Permanent HTTP error: {status}",
                url=url,
                status_code=status,
            )

        if 400 <= status < 500:
            return PermanentError(
                f"Client HTTP error: {status}",
                url=url,
                status_code=status,
            )

        return None

    def _record_final_error(self, url: str, error: Exception) -> None:
        error_record = {
            "url": url,
            "type": type(error).__name__,
            "message": str(error),
            "status_code": getattr(error, "status_code", None),
        }

        self.error_history.append(error_record)

        if isinstance(error, PermanentError):
            self.permanent_error_urls[url] = str(error)

    def _get_request_timeout(self) -> aiohttp.ClientTimeout | None:
        if self.total_timeout is None:
            return None

        attempt = self.retry_strategy.current_attempt
        multiplier = self.timeout_backoff_factor ** attempt

        connect_timeout = self._timeout.connect
        read_timeout = self._timeout.sock_read

        return aiohttp.ClientTimeout(
            total=self.total_timeout * multiplier,
            connect=(
                connect_timeout * multiplier
                if connect_timeout is not None
                else None
            ),
            sock_read=(
                read_timeout * multiplier
                if read_timeout is not None
                else None
            ),
        )

    async def _fetch_url_once(self, url: str) -> str:
        async with self._semaphore:
            logger.info("Start loading URL: %s", url)

            try:
                session = await self._get_session()
                headers = {"User-Agent": self.user_agent}

                request_timeout = self._get_request_timeout()
                request_kwargs = {"headers": headers}

                if request_timeout is not None:
                    request_kwargs["timeout"] = request_timeout

                async with session.get(url, **request_kwargs) as response:
                    classified_error = self._classify_http_status(
                        response.status,
                        url,
                    )

                    if classified_error is not None:
                        raise classified_error

                    text = await response.text()

                    logger.info(
                        "Successfully loaded URL: %s | status=%s | bytes=%s",
                        url,
                        response.status,
                        len(text),
                    )

                    return text

            except CrawlerError:
                raise

            except asyncio.TimeoutError as error:
                raise TransientError(
                    "Timeout while loading URL",
                    url=url,
                    original_error=error,
                ) from error

            except aiohttp.ClientResponseError as error:
                classified_error = self._classify_http_status(
                    error.status,
                    url,
                )

                if classified_error is not None:
                    raise classified_error from error

                raise NetworkError(
                    "HTTP client response error",
                    url=url,
                    status_code=error.status,
                    original_error=error,
                ) from error

            except aiohttp.ClientError as error:
                raise NetworkError(
                    "Network error while loading URL",
                    url=url,
                    original_error=error,
                ) from error

    async def _execute_request_with_policy(
        self,
        url: str,
        operation,
        failure_factory,
    ):
        is_allowed = await self._is_allowed_by_robots(url)

        if not is_allowed:
            return failure_factory()

        async def protected_operation():
            await self._wait_before_request(url)
            self._record_request()

            current_depth = self._request_policy_depth.get()
            token = self._request_policy_depth.set(current_depth + 1)

            try:
                result = await operation(url)
            finally:
                self._request_policy_depth.reset(token)

            if not self._request_result_is_successful(result):
                raise TransientError(
                    "Request returned empty or failed result",
                    url=url,
                )

            return result

        try:
            return await self.retry_strategy.execute_with_retry(
                protected_operation,
            )

        except Exception as error:
            self._record_final_error(url, error)

            logger.warning(
                "Request failed after retry policy: %s | url=%s | error=%s",
                type(error).__name__,
                url,
                error,
            )

            return failure_factory()

    def get_error_stats(self) -> dict:
        retry_delays = self.retry_strategy.retry_delays

        average_retry_delay = (
            sum(retry_delays) / len(retry_delays)
            if retry_delays
            else 0.0
        )

        return {
            "errors_by_type": dict(self.retry_strategy.errors_by_type),
            "successful_retries": self.retry_strategy.successful_retries,
            "failed_after_retries": self.retry_strategy.failed_after_retries,
            "average_retry_delay": average_retry_delay,
            "permanent_error_urls": list(self.permanent_error_urls.keys()),
            "total_error_events": sum(
                self.retry_strategy.errors_by_type.values()
            ),
            "final_failures": len(self.error_history),
        }
    
    def get_error_report(self) -> dict:
        return {
            "error_stats": self.get_error_stats(),
            "error_history": list(self.error_history),
            "permanent_errors": dict(self.permanent_error_urls),
            "retry_delays": list(self.retry_strategy.retry_delays),
        }
