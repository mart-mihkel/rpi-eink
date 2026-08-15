"""Command-line entry point for the eInk dashboard."""

import asyncio
from typing import Literal

from click import Choice, group, option
from returns.io import IOFailure
from returns.result import Failure, Success

from eink.logging import logger, setup_logging

log_level_opt = option(
    "--log-level",
    "-l",
    type=Choice(["debug", "info", "warning", "error"]),
    default="info",
    show_default=True,
    help="Log level",
)


@group(context_settings={"help_option_names": ["-h", "--help"]})
def app() -> None:
    """Run the eInk dashboard command-line application."""


@app.command(help="Fetch OpenMeteo data")
@log_level_opt
def fetch(log_level: Literal["debug", "info", "warning", "error"]) -> None:
    """Fetch OpenMeteo data."""
    from eink.scripts.fetch import main  # noqa: PLC0415

    setup_logging(log_level)
    match asyncio.run(main()):
        case IOFailure(Failure(err)):
            logger.error(err)


@app.command(help="Run the vendored WaveShare e-Paper display demo")
@log_level_opt
def demo(log_level: Literal["debug", "info", "warning", "error"]) -> None:
    """Run the e-Paper display demo, logging any hardware failure."""
    from eink.scripts.demo import main  # noqa: PLC0415

    setup_logging(log_level)
    match main():
        case Success(_):
            pass
        case Failure(err):
            logger.error(err)


if __name__ == "__main__":
    app()
