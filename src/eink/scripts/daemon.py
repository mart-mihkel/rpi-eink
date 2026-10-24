"""Run the dashboard update on a schedule, tolerating network outages."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
from returns.io import IOSuccess
from returns.result import Failure, Success
from returns.unsafe import unsafe_perform_io

from eink.logging import logger
lazy from eink.scripts.update import main as run_update

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from returns.io import IOResult
    from returns.result import Result

    type UpdateFn = Callable[[], Awaitable[Result[None, Exception]]]
    type SleepFn = Callable[[float], Awaitable[None]]

_network_errors: tuple[type[BaseException], ...] = (httpx.HTTPError, OSError)
"""Exceptions that signal the Pi is offline rather than broken."""


def is_network_error(error: BaseException) -> bool:
    """Check whether an error, possibly wrapped, signals a network outage."""
    seen: set[int] = set()
    stack: list[BaseException] = [error]
    while stack:
        current = stack.pop()
        if id(current) in seen:
            continue

        seen.add(id(current))
        if isinstance(current, _network_errors):
            return True

        if current.__cause__ is not None:
            stack.append(current.__cause__)

        if current.__context__ is not None:
            stack.append(current.__context__)

    return False


def _root_cause(error: BaseException) -> BaseException:
    """Return the deepest wrapped exception for readable logging."""
    seen: set[int] = set()
    current = error
    while id(current) not in seen:
        seen.add(id(current))
        inner = current.__cause__ or current.__context__
        if inner is None:
            return current

        current = inner

    return current


@dataclass(frozen=True, slots=True)
class DaemonConfig:
    """Schedule for the update daemon."""

    interval: float = 3600.0
    """Seconds between successful updates."""

    retry_interval: float = 60.0
    """Seconds between attempts while offline."""

    dither: bool = True
    """Use Floyd-Steinberg dithering when converting."""

    def __post_init__(self) -> None:
        """
        Validate the schedule.

        Raises
        ------
        ValueError
            If either interval is not positive.

        """
        if self.interval <= 0:
            msg = f"interval must be positive, got {self.interval}"
            raise ValueError(msg)

        if self.retry_interval <= 0:
            msg = f"retry_interval must be positive, got {self.retry_interval}"
            raise ValueError(msg)


def _to_result(io_result: IOResult[None, Exception]) -> Result[None, Exception]:
    """Flatten a future-safe ``IOResult`` into a plain ``Result``."""
    if isinstance(io_result, IOSuccess):
        return Success(None)

    return Failure(unsafe_perform_io(io_result.failure()))


async def run_daemon(
    config: DaemonConfig,
    *,
    update: UpdateFn,
    sleep: SleepFn = asyncio.sleep,
) -> None:
    """Run ``update`` hourly, retrying quickly while the network is down."""
    logger.info(
        "starting update daemon interval=%ss retry_interval=%ss dither=%s",
        config.interval,
        config.retry_interval,
        config.dither,
    )

    delay = 0.0
    while True:
        if delay > 0:
            await sleep(delay)

        result = await update()
        if isinstance(result, Success):
            logger.info(
                "update succeeded; next update in %.0f seconds",
                config.interval,
            )

            delay = config.interval
            continue

        failure = result.failure()
        cause = _root_cause(failure)
        if is_network_error(failure):
            logger.warning(
                "update failed (%r); retrying in %.0f seconds",
                cause,
                config.retry_interval,
            )

            delay = config.retry_interval
        else:
            logger.error(
                "update failed (%r); next update in %.0f seconds",
                cause,
                config.interval,
            )

            delay = config.interval


async def main(config: DaemonConfig) -> None:
    """Run the update daemon with the real hardware update."""

    async def _update() -> Result[None, Exception]:
        return _to_result(await run_update(dither=config.dither))

    await run_daemon(config, update=_update)
