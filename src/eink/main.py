"""Command-line entry point for the eInk dashboard."""

import asyncio
from pathlib import Path
from typing import get_args

from click import Choice, argument, group, option
from click import Path as ClickPath

from eink.constants import DATA
from eink.logging import setup_logging
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


@app.command(help="Fetch weather data and render the dashboard image")
@option(
    "--output",
    "-o",
    type=ClickPath(dir_okay=False, path_type=Path),
    default=DATA / "render.png",
    show_default=True,
    help="Output image path",
)
@log_level_opt
def render(output: Path, log_level: LogLevel) -> None:
    """Fetch the forecast and render it as a dashboard image."""
    from eink.scripts.render import main  # noqa: PLC0415

    setup_logging(log_level)
    asyncio.run(main(output)).unwrap()


@app.command(help="Fetch, render, convert, and display the weather dashboard")
@option("--dither/--no-dither", default=True, help="Use Floyd-Steinberg dithering")
@log_level_opt
def update(*, log_level: LogLevel, dither: bool) -> None:
    """Fetch weather, render it, convert it, and show it on the panel."""
    from eink.scripts.update import main  # noqa: PLC0415

    setup_logging(log_level)
    asyncio.run(main(dither=dither)).unwrap()


@app.command(help="Run the vendored WaveShare e-Paper display demo")
@log_level_opt
def demo(log_level: LogLevel) -> None:
    """Run the e-Paper display demo, logging any hardware failure."""
    from eink.scripts.demo import main  # noqa: PLC0415

    setup_logging(log_level)
    main().unwrap()


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
    from eink.scripts.convert import main  # noqa: PLC0415

    _dest = dest if dest is not None else src.with_suffix(".bmp")

    setup_logging(log_level)
    main(src, dest, dither=dither).unwrap()


@app.command(help="Display an image on the e-Paper panel")
@argument("path", type=ClickPath(exists=True, dir_okay=False, path_type=Path))
@log_level_opt
def display(path: Path, *, log_level: LogLevel) -> None:
    """Show PATH on the panel, then put it back to sleep."""
    from eink.scripts.display import main  # noqa: PLC0415

    setup_logging(log_level)
    main(path).unwrap()


if __name__ == "__main__":
    app()
