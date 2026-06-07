class CrawlerError(Exception):
    def __init__(
        self,
        message: str = "",
        url: str | None = None,
        status_code: int | None = None,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(message)

        self.message = message
        self.url = url
        self.status_code = status_code
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message or self.__class__.__name__]

        if self.url is not None:
            parts.append(f"url={self.url}")

        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")

        if self.original_error is not None:
            parts.append(f"original_error={type(self.original_error).__name__}")

        return " | ".join(parts)


class TransientError(CrawlerError):
    """Временная ошибка: 429, 500, 503, timeout."""


class PermanentError(CrawlerError):
    """Постоянная ошибка: 401, 403, 404."""


class NetworkError(CrawlerError):
    """Сетевая ошибка: DNS, connection refused, connection reset."""


class ParseError(CrawlerError):
    """Ошибка парсинга HTML."""
