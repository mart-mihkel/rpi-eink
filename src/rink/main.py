"""Command-line entry point for the eInk dashboard."""

import asyncio
from pathlib import Path
from typing import get_args

import rich_click as click

from rink.logging import logger, setup_logging
from rink.types import LogLevel
lazy from rink.scripts.convert import main as convert_main
lazy from rink.scripts.daemon import DaemonConfig
lazy from rink.scripts.daemon import main as weather_daemon_main
lazy from rink.scripts.demo import main as demo_main
lazy from rink.scripts.display import main as display_main
lazy from rink.scripts.slideshow import DirDaemonConfig
lazy from rink.scripts.slideshow import main as dir_daemon_main
lazy from rink.scripts.update import main as weather_update_main


@click.group(
    "rink",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Run the eInk dashboard command-line application.",
    no_args_is_help=True,
)
@click.rich_config(
    click.RichHelpConfiguration(
        theme="cargo-slim",
        command_groups={
            "rink": [
                {
                    "name": "Weather",
                    "commands": ["weather-update", "weather-daemon"],
                },
                {
                    "name": "Display",
                    "commands": ["dir-daemon", "display"],
                },
                {
                    "name": "Tools",
                    "commands": ["demo", "convert"],
                },
            ],
        },
        option_groups={
            "rink *": [
                {"name": "Input", "options": ["--src", "--output"]},
                {
                    "name": "Schedule",
                    "options": [
                        "--interval",
                        "--retry-interval",
                        "--recursive",
                        "--seed",
                    ],
                },
                {"name": "Rendering", "options": ["--dither"]},
                {"name": "Run", "options": ["--log-level"]},
            ],
        },
    )
)
def app() -> None:
    """Run the eInk dashboard command-line application."""
    setup_logging()


log_level = click.option(
    "--log-level",
    "-ll",
    type=click.Choice(get_args(LogLevel)),
    default="info",
    show_default=True,
    help="Log level",
)

dither = click.option(
    "--dither/--no-dither",
    default=True,
    help="Use Floyd-Steinberg dithering",
)


@app.command(
    "weather-update",
    help="Fetch, render, convert, and display the weather dashboard",
)
@dither
@log_level
def weather_update(*, dither: bool, log_level: LogLevel) -> None:
    """Fetch weather, render it, convert it, and show it on the panel."""
    logger.setLevel(log_level.upper())
    asyncio.run(weather_update_main(dither=dither)).unwrap()


@app.command(
    "weather-daemon",
    help="Run the dashboard update hourly, waiting out network outages",
)
@click.option(
    "--interval",
    "-i",
    type=float,
    default=3600.0,
    show_default=True,
    help="Seconds between successful updates",
)
@click.option(
    "--retry-interval",
    "-r",
    type=float,
    default=60.0,
    show_default=True,
    help="Seconds between attempts while offline",
)
@dither
@log_level
def weather_daemon(
    *,
    interval: float,
    retry_interval: float,
    dither: bool,
    log_level: LogLevel,
) -> None:
    """Update hourly; on network errors retry until reconnected, then resume."""
    if interval <= 0:
        msg = "interval must be positive"
        raise click.BadParameter(msg, param_hint="--interval")
    if retry_interval <= 0:
        msg = "retry_interval must be positive"
        raise click.BadParameter(msg, param_hint="--retry-interval")

    logger.setLevel(log_level.upper())
    config = DaemonConfig(
        interval=interval,
        retry_interval=retry_interval,
        dither=dither,
    )
    try:
        asyncio.run(weather_daemon_main(config))
    except KeyboardInterrupt:
        logger.info("update daemon stopped")


@app.command(
    "dir-daemon",
    help="Show random images from a directory on a schedule",
)
@click.option(
    "--src",
    type=click.Path(path_type=Path),
    required=True,
    help="Source directory with images",
)
@click.option(
    "--interval",
    "-i",
    type=float,
    default=600.0,
    show_default=True,
    help="Seconds between images",
)
@click.option(
    "--recursive/--no-recursive",
    default=False,
    show_default=True,
    help="Search subdirectories too",
)
@dither
@log_level
def dir_daemon(
    *,
    src: Path,
    interval: float,
    recursive: bool,
    dither: bool,
    log_level: LogLevel,
) -> None:
    """Pick random images from SRC, convert, and show them until an error stops."""
    if interval <= 0:
        msg = "interval must be positive"
        raise click.BadParameter(msg, param_hint="--interval")
    if not src.is_dir():
        msg = f"src must be a directory, got {src}"
        raise click.BadParameter(msg, param_hint="--src")

    logger.setLevel(log_level.upper())
    config = DirDaemonConfig(
        source=src,
        interval=interval,
        recursive=recursive,
        dither=dither,
    )

    try:
        asyncio.run(dir_daemon_main(config))
    except KeyboardInterrupt:
        logger.info("dir daemon stopped")
    except Exception as exc:
        msg = f"dir daemon failed: {exc}"
        raise click.ClickException(msg) from exc


@app.command(
    "demo",
    help="Run the vendored WaveShare e-Paper display demo",
)
@log_level
def demo(*, log_level: LogLevel) -> None:
    """Run the e-Paper display demo, logging any hardware failure."""
    logger.setLevel(log_level.upper())
    demo_main().unwrap()


@app.command(
    "convert",
    help="Convert an image into a panel-ready BMP",
)
@click.argument(
    "src",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "dest",
    type=click.Path(dir_okay=False, path_type=Path),
    required=False,
)
@dither
@log_level
def convert(
    src: Path,
    dest: Path | None,
    *,
    dither: bool,
    log_level: LogLevel,
) -> None:
    """Fit and quantize."""
    logger.setLevel(log_level.upper())
    convert_main(src, dest, dither=dither).unwrap()


@app.command(
    "display",
    help="Display an image, converting non-BMP sources for the panel",
)
@click.argument(
    "src",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@log_level
def display(src: Path, *, log_level: LogLevel) -> None:
    """Show PATH on the panel, then put it back to sleep."""
    logger.setLevel(log_level.upper())
    display_main(src).unwrap()


if __name__ == "__main__":
    app()
