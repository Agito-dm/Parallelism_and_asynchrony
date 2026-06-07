import asyncio
import logging
from contextvars import ContextVar

from crawler_day5.errors import NetworkError, TransientError

logger = logging.getLogger(__name__)


class RetryStrategy:
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_on: list[type[Exception]] | None = None,
        base_delay: float = 1.0,
        retry_limits: dict[type[Exception], int] | None = None,
        backoff_by_error: dict[type[Exception], float] | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        if backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")

        if base_delay < 0:
            raise ValueError("base_delay must be non-negative")

        if retry_limits is not None:
            for error_type, limit in retry_limits.items():
                if not issubclass(error_type, Exception):
                    raise TypeError("retry_limits keys must be exception types")

                if limit < 0:
                    raise ValueError("retry limit must be non-negative")

        if backoff_by_error is not None:
            for error_type, factor in backoff_by_error.items():
                if not issubclass(error_type, Exception):
                    raise TypeError("backoff_by_error keys must be exception types")

                if factor < 0:
                    raise ValueError("backoff factor must be non-negative")

        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.base_delay = base_delay

        self.retry_on = tuple(retry_on) if retry_on is not None else (
            TransientError,
            NetworkError,
        )

        self.retry_limits = retry_limits or {}
        self.backoff_by_error = backoff_by_error or {}

        self.retry_delays: list[float] = []
        self.total_attempts = 0
        self.successful_retries = 0
        self.failed_after_retries = 0
        self.errors_by_type: dict[str, int] = {}

        self._current_attempt: ContextVar[int] = ContextVar(
            "retry_current_attempt",
            default=0,
        )

    def is_retryable(self, error: Exception) -> bool:
        return isinstance(error, self.retry_on)

    def _record_error(self, error: Exception) -> None:
        error_type = type(error).__name__
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1

    def _get_retry_limit_for_error(self, error: Exception) -> int:
        for error_type, limit in self.retry_limits.items():
            if isinstance(error, error_type):
                return limit

        return self.max_retries

    def _get_backoff_factor_for_error(self, error: Exception) -> float:
        for error_type, factor in self.backoff_by_error.items():
            if isinstance(error, error_type):
                return factor

        return self.backoff_factor

    def get_delay(self, attempt: int, error: Exception | None = None) -> float:
        if error is None:
            factor = self.backoff_factor
        else:
            factor = self._get_backoff_factor_for_error(error)

        return self.base_delay * (factor ** attempt)

    async def _sleep(self, delay: float) -> None:
        await asyncio.sleep(delay)

    async def execute_with_retry(self, coro, *args, **kwargs):
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            self.total_attempts += 1

            token = self._current_attempt.set(attempt)

            try:
                result = await coro(*args, **kwargs)

            except Exception as error:
                self._current_attempt.reset(token)

                last_error = error
                self._record_error(error)

                if not self.is_retryable(error):
                    logger.warning(
                        "Non-retryable error: %s | attempt=%s | error=%s",
                        type(error).__name__,
                        attempt + 1,
                        error,
                    )
                    raise

                retry_limit = self._get_retry_limit_for_error(error)

                if attempt >= retry_limit:
                    self.failed_after_retries += 1
                    logger.warning(
                        "Retry limit reached: %s | attempts=%s | error=%s",
                        type(error).__name__,
                        attempt + 1,
                        error,
                    )
                    raise

                delay = self.get_delay(attempt, error)
                self.retry_delays.append(delay)

                logger.warning(
                    "Retryable error: %s | attempt=%s | next_delay=%.3fs | error=%s",
                    type(error).__name__,
                    attempt + 1,
                    delay,
                    error,
                )

                await self._sleep(delay)

            else:
                self._current_attempt.reset(token)

                if attempt > 0:
                    self.successful_retries += 1

                    logger.info(
                        "Retry succeeded | attempt=%s",
                        attempt + 1,
                    )

                return result

        if last_error is not None:
            raise last_error

        raise RuntimeError("RetryStrategy finished without result or error")
    
    @property
    def current_attempt(self) -> int:
        return self._current_attempt.get()
