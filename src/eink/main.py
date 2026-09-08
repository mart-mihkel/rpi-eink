"""Command-line entry point for the eInk dashboard."""

import asyncio
from pathlib import Path  # noqa: TC003 - typer resolves annotations at runtime
from typing import Annotated

import typer

from eink.constants import DATA
from eink.logging import logger, setup_logging
from eink.types import LogLevel

app = typer.Typer(
    help="Run the eInk dashboard command-line application.",
    add_completion=False,
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)

LogLevelOption = Annotated[
    LogLevel,
    typer.Option("--log-level", "-l", help="Log level"),
]
DitherOption = Annotated[
    bool,
    typer.Option(help="Use Floyd-Steinberg dithering"),
]


@app.command(help="Fetch weather data and render the dashboard image")
def render(
    *,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", dir_okay=False, help="Output image path"),
    ] = DATA / "render.png",
    log_level: LogLevelOption = "info",
) -> None:
    """Fetch the forecast and render it as a dashboard image."""
    from eink.scripts.render import main  # noqa: PLC0415

    setup_logging(log_level)
    asyncio.run(main(output)).unwrap()


@app.command(help="Fetch, render, convert, and display the weather dashboard")
def update(
    *,
    dither: DitherOption = True,
    log_level: LogLevelOption = "info",
) -> None:
    """Fetch weather, render it, convert it, and show it on the panel."""
    from eink.scripts.update import main  # noqa: PLC0415

    setup_logging(log_level)
    asyncio.run(main(dither=dither)).unwrap()


@app.command(help="Run the dashboard update hourly, waiting out network outages")
def daemon(
    *,
    interval: Annotated[
        float,
        typer.Option("--interval", "-i", help="Seconds between successful updates"),
    ] = 3600.0,
    retry_interval: Annotated[
        float,
        typer.Option(
            "--retry-interval",
            "-r",
            help="Seconds between attempts while offline",
        ),
    ] = 60.0,
    dither: DitherOption = True,
    log_level: LogLevelOption = "info",
) -> None:
    """Update hourly; on network errors retry until reconnected, then resume."""
    from eink.scripts.daemon import DaemonConfig  # noqa: PLC0415
    from eink.scripts.daemon import main as daemon_main  # noqa: PLC0415

    if interval <= 0:
        msg = "interval must be positive"
        raise typer.BadParameter(msg)
    if retry_interval <= 0:
        msg = "retry_interval must be positive"
        raise typer.BadParameter(msg)

    setup_logging(log_level)
    config = DaemonConfig(
        interval=interval,
        retry_interval=retry_interval,
        dither=dither,
    )
    try:
        asyncio.run(daemon_main(config))
    except KeyboardInterrupt:
        logger.info("update daemon stopped")


@app.command(help="Run the vendored WaveShare e-Paper display demo")
def demo(log_level: LogLevelOption = "info") -> None:
    """Run the e-Paper display demo, logging any hardware failure."""
    from eink.scripts.demo import main  # noqa: PLC0415

    setup_logging(log_level)
    main().unwrap()


@app.command(help="Convert an image into a panel-ready BMP")
def convert(
    src: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="Source image"),
    ],
    dest: Annotated[
        Path | None,
        typer.Argument(dir_okay=False, help="Destination BMP"),
    ] = None,
    *,
    dither: DitherOption = True,
    log_level: LogLevelOption = "info",
) -> None:
    """Fit and quantize."""
    from eink.scripts.convert import main  # noqa: PLC0415

    setup_logging(log_level)
    main(src, dest, dither=dither).unwrap()


@app.command(help="Display an image on the e-Paper panel")
def display(
    path: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, help="Image to show"),
    ],
    *,
    log_level: LogLevelOption = "info",
) -> None:
    """Show PATH on the panel, then put it back to sleep."""
    from eink.scripts.display import main  # noqa: PLC0415

    setup_logging(log_level)
    main(path).unwrap()


if __name__ == "__main__":
    app()
