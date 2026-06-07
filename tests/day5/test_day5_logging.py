import logging

import pytest

from crawler_day5.errors import PermanentError, TransientError
from crawler_day5.retry_strategy import RetryStrategy


async def test_day5_retry_strategy_logs_retryable_error_and_success(
    monkeypatch,
    caplog,
):
    strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )
    calls = 0

    async def fake_sleep(delay: float) -> None:
        return None

    async def flaky_task():
        nonlocal calls
        calls += 1

        if calls == 1:
            raise TransientError(
                "temporary error",
                url="https://example.com/temporary",
                status_code=503,
            )

        return "ok"

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    caplog.set_level(logging.INFO)

    result = await strategy.execute_with_retry(flaky_task)

    assert result == "ok"
    assert calls == 2

    assert "Retryable error: TransientError" in caplog.text
    assert "attempt=1" in caplog.text
    assert "next_delay=0.000s" in caplog.text
    assert "https://example.com/temporary" in caplog.text
    assert "status_code=503" in caplog.text
    assert "Retry succeeded" in caplog.text
    assert "attempt=2" in caplog.text


async def test_day5_retry_strategy_logs_non_retryable_error(caplog):
    strategy = RetryStrategy(
        max_retries=3,
        base_delay=0.0,
    )

    async def failing_task():
        raise PermanentError(
            "not found",
            url="https://example.com/missing",
            status_code=404,
        )

    caplog.set_level(logging.WARNING)

    with pytest.raises(PermanentError):
        await strategy.execute_with_retry(failing_task)

    assert "Non-retryable error: PermanentError" in caplog.text
    assert "attempt=1" in caplog.text
    assert "https://example.com/missing" in caplog.text
    assert "status_code=404" in caplog.text


async def test_day5_retry_strategy_logs_retry_limit_reached(
    monkeypatch,
    caplog,
):
    strategy = RetryStrategy(
        max_retries=1,
        base_delay=0.0,
    )

    async def fake_sleep(delay: float) -> None:
        return None

    async def always_failing_task():
        raise TransientError(
            "service unavailable",
            url="https://example.com/unavailable",
            status_code=503,
        )

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    caplog.set_level(logging.WARNING)

    with pytest.raises(TransientError):
        await strategy.execute_with_retry(always_failing_task)

    assert "Retryable error: TransientError" in caplog.text
    assert "Retry limit reached: TransientError" in caplog.text
    assert "attempts=2" in caplog.text
    assert "https://example.com/unavailable" in caplog.text
    assert "status_code=503" in caplog.text
