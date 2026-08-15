"""Command-line entry point for the eInk dashboard."""

import asyncio
from pathlib import Path
from typing import get_args

from click import Choice, argument, group, option
from click import Path as ClickPath
from returns.io import IOFailure
from returns.result import Failure

from eink.logging import logger, setup_logging
from eink.types import LogLevel

log_level_opt = option(
    "--log-level",
    "-l",
    type=Choice(get_args(LogLevel.__value__)),
    default="info",
    show_default=True,
    help="Log level",
)


@group(context_settings={"help_option_names": ["-h", "--help"]})
def app() -> None:
    """Run the eInk dashboard command-line application."""


@app.command(help="Fetch OpenMeteo data")
@log_level_opt
def fetch(log_level: LogLevel) -> None:
    """Fetch OpenMeteo data."""
    from eink.scripts.fetch import main  # noqa: PLC0415

    setup_logging(log_level)
    match asyncio.run(main()):
        case IOFailure(Failure(err)):
            logger.error(err)


@app.command(help="Run the vendored WaveShare e-Paper display demo")
@log_level_opt
def demo(log_level: LogLevel) -> None:
    """Run the e-Paper display demo, logging any hardware failure."""
    from eink.scripts.demo import main  # noqa: PLC0415

    setup_logging(log_level)
    match main():
        case Failure(err):
            logger.error(err)


@app.command(help="Convert an image into a panel-ready BMP")
@argument("src", type=ClickPath(exists=True, dir_okay=False, path_type=Path))
@argument("dest", type=ClickPath(dir_okay=False, path_type=Path), required=False)
@option("--dither/--no-dither", default=True, help="Use Floyd-Steinberg dithering")
@log_level_opt
def convert(
    src: Path,
    dest: Path | None,
    *,
    log_level: LogLevel,
    dither: bool,
) -> None:
    """Fit and quantize."""
    from eink.scripts.convert import convert as convert_image  # noqa: PLC0415

    setup_logging(log_level)
    _dest = dest if dest is not None else src.with_suffix(".bmp")

    match convert_image(src, _dest, dither=dither):
        case Failure(err):
            logger.error(err)


@app.command(help="Display an image on the e-Paper panel")
@argument("path", type=ClickPath(exists=True, dir_okay=False, path_type=Path))
@log_level_opt
def display(path: Path, *, log_level: LogLevel) -> None:
    """Show PATH on the panel, then put it back to sleep."""
    from eink.scripts.display import display as display_image  # noqa: PLC0415

    setup_logging(log_level)
    match display_image(path):
        case Failure(err):
            logger.error(err)


if __name__ == "__main__":
    app()
