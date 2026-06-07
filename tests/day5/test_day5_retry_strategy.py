import pytest

from crawler_day5.errors import (
    NetworkError,
    ParseError,
    PermanentError,
    TransientError,
)
from crawler_day5.retry_strategy import RetryStrategy


async def test_retry_strategy_success_without_retry():
    strategy = RetryStrategy(max_retries=3)
    calls = 0

    async def successful_task():
        nonlocal calls
        calls += 1
        return "ok"

    result = await strategy.execute_with_retry(successful_task)

    assert result == "ok"
    assert calls == 1
    assert strategy.total_attempts == 1
    assert strategy.retry_delays == []
    assert strategy.successful_retries == 0
    assert strategy.failed_after_retries == 0


async def test_retry_strategy_retries_transient_error_then_succeeds(monkeypatch):
    strategy = RetryStrategy(
        max_retries=3,
        backoff_factor=2.0,
        base_delay=0.5,
    )
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def flaky_task():
        nonlocal calls
        calls += 1

        if calls <= 2:
            raise TransientError("temporary error")

        return "ok"

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    result = await strategy.execute_with_retry(flaky_task)

    assert result == "ok"
    assert calls == 3
    assert sleep_delays == [0.5, 1.0]
    assert strategy.retry_delays == [0.5, 1.0]
    assert strategy.successful_retries == 1
    assert strategy.failed_after_retries == 0
    assert strategy.errors_by_type["TransientError"] == 2


async def test_retry_strategy_retries_network_error_then_succeeds(monkeypatch):
    strategy = RetryStrategy(max_retries=2, base_delay=0.1)
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def flaky_task():
        nonlocal calls
        calls += 1

        if calls == 1:
            raise NetworkError("network problem")

        return "ok"

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    result = await strategy.execute_with_retry(flaky_task)

    assert result == "ok"
    assert calls == 2
    assert sleep_delays == [0.1]
    assert strategy.successful_retries == 1
    assert strategy.errors_by_type["NetworkError"] == 1


async def test_retry_strategy_does_not_retry_permanent_error(monkeypatch):
    strategy = RetryStrategy(max_retries=3)
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def failing_task():
        nonlocal calls
        calls += 1
        raise PermanentError("not found", status_code=404)

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    with pytest.raises(PermanentError):
        await strategy.execute_with_retry(failing_task)

    assert calls == 1
    assert sleep_delays == []
    assert strategy.retry_delays == []
    assert strategy.failed_after_retries == 0
    assert strategy.errors_by_type["PermanentError"] == 1


async def test_retry_strategy_does_not_retry_parse_error_by_default(monkeypatch):
    strategy = RetryStrategy(max_retries=3)
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def failing_task():
        nonlocal calls
        calls += 1
        raise ParseError("parse failed")

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    with pytest.raises(ParseError):
        await strategy.execute_with_retry(failing_task)

    assert calls == 1
    assert sleep_delays == []
    assert strategy.errors_by_type["ParseError"] == 1


async def test_retry_strategy_raises_after_max_retries(monkeypatch):
    strategy = RetryStrategy(
        max_retries=2,
        backoff_factor=2.0,
        base_delay=1.0,
    )
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def always_failing_task():
        nonlocal calls
        calls += 1
        raise TransientError("still failing")

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    with pytest.raises(TransientError):
        await strategy.execute_with_retry(always_failing_task)

    assert calls == 3
    assert sleep_delays == [1.0, 2.0]
    assert strategy.retry_delays == [1.0, 2.0]
    assert strategy.failed_after_retries == 1
    assert strategy.errors_by_type["TransientError"] == 3


async def test_retry_strategy_can_retry_custom_error_type(monkeypatch):
    strategy = RetryStrategy(
        max_retries=1,
        retry_on=[ParseError],
        base_delay=0.1,
    )
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def flaky_parse_task():
        nonlocal calls
        calls += 1

        if calls == 1:
            raise ParseError("temporary parser issue")

        return "parsed"

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    result = await strategy.execute_with_retry(flaky_parse_task)

    assert result == "parsed"
    assert calls == 2
    assert sleep_delays == [0.1]
    assert strategy.successful_retries == 1


async def test_retry_strategy_uses_retry_limit_for_specific_error_type(monkeypatch):
    strategy = RetryStrategy(
        max_retries=5,
        base_delay=0.1,
        retry_limits={
            TransientError: 1,
        },
    )
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def always_failing_task():
        nonlocal calls
        calls += 1
        raise TransientError("temporary error")

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    with pytest.raises(TransientError):
        await strategy.execute_with_retry(always_failing_task)

    assert calls == 2
    assert sleep_delays == [0.1]
    assert strategy.failed_after_retries == 1


async def test_retry_strategy_uses_backoff_factor_for_specific_error_type(monkeypatch):
    strategy = RetryStrategy(
        max_retries=3,
        backoff_factor=2.0,
        base_delay=1.0,
        backoff_by_error={
            NetworkError: 3.0,
        },
    )
    calls = 0
    sleep_delays: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleep_delays.append(delay)

    async def flaky_network_task():
        nonlocal calls
        calls += 1

        if calls <= 2:
            raise NetworkError("network error")

        return "ok"

    monkeypatch.setattr(strategy, "_sleep", fake_sleep)

    result = await strategy.execute_with_retry(flaky_network_task)

    assert result == "ok"
    assert calls == 3
    assert sleep_delays == [1.0, 3.0]
    assert strategy.retry_delays == [1.0, 3.0]
