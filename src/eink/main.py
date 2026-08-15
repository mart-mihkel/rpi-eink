"""Command-line entry point for the eInk dashboard."""

import asyncio
from typing import Literal

from click import Choice, group, option
from returns.future import future
from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success

from eink.logging import logger, setup_logging
from eink.weather import OpenMeteoClient


@group(context_settings={"help_option_names": ["-h", "--help"]})
@option(
    "--log-level",
    "-l",
    type=Choice(["debug", "info", "warning", "error"]),
    default="info",
    show_default=True,
    help="Log level",
)
def app(log_level: Literal["debug", "info", "warning", "error"]) -> None:
    """Run the eInk dashboard command-line application."""
    setup_logging(log_level)


@app.command(help="Fetch OpenMeteo data")
def fetch() -> None:
    """Fetch OpenMeteo data."""
    asyncio.run(_fetch())


@future
async def _fetch() -> None:
    """Fetch weather data and close the asynchronous client."""
    client = OpenMeteoClient()

    match await client.get_forecast():
        case IOSuccess(Success(forecast)):
            pass
        case IOFailure(Failure(err)):
            logger.error(err)

    match await client.get_current():
        case IOSuccess(Success(current)):
            pass
        case IOFailure(Failure(err)):
            logger.error(err)
            return

    await client.close()

    logger.info(current)
    logger.info(forecast)


if __name__ == "__main__":
    app()
