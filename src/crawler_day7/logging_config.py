import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


DEFAULT_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def setup_logging(
    *,
    level: str = "INFO",
    filename: str | None = None,
    max_bytes: int = 1_000_000,
    backup_count: int = 3,
    console: bool = True,
) -> None:
    numeric_level = _parse_log_level(level)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    root_logger.handlers.clear()

    formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if filename:
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def _parse_log_level(level: str) -> int:
    numeric_level = getattr(logging, level.upper(), None)

    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    return numeric_level
