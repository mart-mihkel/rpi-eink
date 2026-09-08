"""Tests for the update daemon."""

from typing import TYPE_CHECKING

import httpx
import pytest
from returns.future import future_safe
from returns.result import Failure, Result, Success

from eink.scripts.daemon import DaemonConfig, _to_result, is_network_error, run_daemon

if TYPE_CHECKING:
    from collections.abc import Iterator

_OFFLINE_MESSAGE = "offline"
_MAX_SLEEPS = 10


@pytest.fixture
def anyio_backend() -> str:
    """Restrict anyio-marked tests to the asyncio backend."""
    return "asyncio"


class _StopError(Exception):
    """Break the daemon's infinite loop once the test has seen enough."""


def _request() -> httpx.Request:
    """Build a request for constructing httpx errors without network access."""
    return httpx.Request("GET", "https://api.open-meteo.com/v1/forecast")


def _offline_error() -> httpx.ConnectError:
    """Build a connection error without touching the network."""
    return httpx.ConnectError(_OFFLINE_MESSAGE, request=_request())


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("down"),
        httpx.ReadTimeout("slow"),
        httpx.NetworkError("lost"),
        OSError("unreachable"),
        TimeoutError("timed out"),
    ],
)
def test_is_network_error_detects_outages(error: BaseException) -> None:
    """Connection, timeout, and OS-level errors count as offline."""
    assert is_network_error(error) is True


async def test_is_network_error_follows_returns_wrapping() -> None:
    """Failures surfaced through `returns` still classify as network errors."""

    @future_safe
    async def _failing() -> None:
        raise _offline_error()

    result = _to_result(await _failing())
    assert isinstance(result, Failure)
    assert is_network_error(result.failure()) is True


async def test_to_result_unwraps_success() -> None:
    """A successful future becomes a plain success."""

    @future_safe
    async def _succeeding() -> None:
        return None

    result = _to_result(await _succeeding())
    assert isinstance(result, Success)


def test_is_network_error_follows_cause_chains() -> None:
    """A generic wrapper around a network error still counts as offline."""
    wrapper = RuntimeError("update failed")
    wrapper.__cause__ = _offline_error()

    assert is_network_error(wrapper) is True


@pytest.mark.parametrize(
    "error",
    [
        ValueError("bad query"),
        KeyError("missing key"),
        RuntimeError("render bug"),
    ],
)
def test_is_network_error_rejects_other_failures(error: BaseException) -> None:
    """Programming and data errors are not retried as outages."""
    assert is_network_error(error) is False


@pytest.mark.parametrize(
    ("interval", "retry_interval"),
    [(0.0, 60.0), (-1.0, 60.0), (3600.0, 0.0), (3600.0, -5.0)],
)
def test_daemon_config_rejects_non_positive_intervals(
    interval: float,
    retry_interval: float,
) -> None:
    """Schedules must wait a positive amount of time."""
    with pytest.raises(ValueError, match="must be positive"):
        DaemonConfig(interval=interval, retry_interval=retry_interval)


async def test_run_daemon_sleeps_hourly_after_success() -> None:
    """A successful update is followed by a full-interval sleep."""
    config = DaemonConfig(interval=3600.0, retry_interval=60.0)
    delays: list[float] = []
    outcomes: Iterator[Result[None, Exception]] = iter([Success(None)])

    async def _update() -> Result[None, Exception]:
        outcome = next(outcomes, None)
        if outcome is None:
            raise _StopError
        return outcome

    async def _sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) >= _MAX_SLEEPS:
            raise _StopError

    with pytest.raises(_StopError):
        await run_daemon(config, update=_update, sleep=_sleep)

    assert delays == [config.interval]


async def test_run_daemon_retries_offline_then_resumes_hourly() -> None:
    """Offline attempts retry quickly; reconnecting updates right away."""
    config = DaemonConfig(interval=3600.0, retry_interval=60.0)
    delays: list[float] = []
    outcomes: Iterator[Result[None, Exception]] = iter(
        [
            Failure(_offline_error()),
            Failure(_offline_error()),
            Success(None),
        ],
    )

    async def _update() -> Result[None, Exception]:
        outcome = next(outcomes, None)
        if outcome is None:
            raise _StopError
        return outcome

    async def _sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) >= _MAX_SLEEPS:
            raise _StopError

    with pytest.raises(_StopError):
        await run_daemon(config, update=_update, sleep=_sleep)

    assert delays == [
        config.retry_interval,
        config.retry_interval,
        config.interval,
    ]


async def test_run_daemon_waits_full_interval_on_unexpected_error() -> None:
    """Non-network failures are logged and retried after a full interval."""
    config = DaemonConfig(interval=3600.0, retry_interval=60.0)
    delays: list[float] = []
    outcomes: Iterator[Result[None, Exception]] = iter(
        [Failure(ValueError("bad data")), Success(None)],
    )

    async def _update() -> Result[None, Exception]:
        outcome = next(outcomes, None)
        if outcome is None:
            raise _StopError
        return outcome

    async def _sleep(delay: float) -> None:
        delays.append(delay)
        if len(delays) >= _MAX_SLEEPS:
            raise _StopError

    with pytest.raises(_StopError):
        await run_daemon(config, update=_update, sleep=_sleep)

    assert delays == [config.interval, config.interval]
