import logging

import pytest

from crawler_day7.logging_config import setup_logging


def test_day7_setup_logging_writes_to_file(tmp_path):
    log_path = tmp_path / "crawler.log"

    setup_logging(
        level="INFO",
        filename=str(log_path),
        console=False,
    )

    logger = logging.getLogger("test_logger")
    logger.info("hello from test")

    for handler in logging.getLogger().handlers:
        handler.flush()

    assert log_path.exists()

    content = log_path.read_text(encoding="utf-8")

    assert "INFO" in content
    assert "test_logger" in content
    assert "hello from test" in content


def test_day7_setup_logging_rotates_log_file(tmp_path):
    log_path = tmp_path / "crawler.log"

    setup_logging(
        level="INFO",
        filename=str(log_path),
        max_bytes=200,
        backup_count=1,
        console=False,
    )

    logger = logging.getLogger("rotation_test")

    for index in range(50):
        logger.info("log line number %s with enough text to trigger rotation", index)

    for handler in logging.getLogger().handlers:
        handler.flush()

    rotated_log_path = tmp_path / "crawler.log.1"

    assert log_path.exists()
    assert rotated_log_path.exists()


def test_day7_setup_logging_rejects_invalid_level():
    with pytest.raises(ValueError, match="Invalid log level"):
        setup_logging(level="NOPE")
