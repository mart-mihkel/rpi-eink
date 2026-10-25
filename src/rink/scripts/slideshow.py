"""Show random images from a directory on a schedule."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

from rink.logging import logger
from rink.scripts.display import display_image, prepare_image

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence
    from pathlib import Path

    type ShowFn = Callable[[Path], None]
    type SleepFn = Callable[[float], Awaitable[None]]

SUPPORTED_SUFFIXES: frozenset[str] = frozenset(
    suffix.lower()
    for suffix, format_name in Image.registered_extensions().items()
    if format_name in Image.OPEN
)
"""Lowercased suffixes Pillow can open; anything else is skipped by the slideshow."""


@dataclass(frozen=True, slots=True)
class DirDaemonConfig:
    """Schedule for the directory slideshow daemon."""

    source: Path
    """Directory to pick random images from."""

    interval: float = 600.0
    """Seconds between images."""

    recursive: bool = False
    """Search subdirectories too."""

    seed: int | None = None
    """Seed for reproducible random order; None for non-deterministic."""

    dither: bool = True
    """Use Floyd-Steinberg dithering when converting."""

    def __post_init__(self) -> None:
        """Validate the schedule."""
        if self.interval <= 0:
            msg = f"interval must be positive, got {self.interval}"
            raise ValueError(msg)


def list_images(source: Path, *, recursive: bool) -> list[Path]:
    """Collect displayable images from a directory."""
    if not source.is_dir():
        msg = f"source must be a directory, got {source}"
        raise NotADirectoryError(msg)

    candidates = source.rglob("*") if recursive else source.iterdir()
    return sorted(
        path
        for path in candidates
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def show_image(path: Path, *, dither: bool = True) -> None:
    """Load an image file, fitting and quantizing it for the panel, then show it."""
    display_image(prepare_image(path, dither=dither))


async def run_dir_daemon(
    config: DirDaemonConfig,
    *,
    show: ShowFn = show_image,
    sleep: SleepFn = asyncio.sleep,
    rng: random.Random | None = None,
) -> None:
    """Show random images from ``config.source`` until a failure stops the loop."""
    _rng = rng if rng is not None else random.Random(config.seed)  # noqa: S311 - slideshow order is not cryptographic
    logger.info(
        "starting dir daemon source=%s interval=%ss recursive=%s dither=%s",
        config.source,
        config.interval,
        config.recursive,
        config.dither,
    )

    while True:
        images: Sequence[Path] = list_images(config.source, recursive=config.recursive)
        if not images:
            msg = f"no images found in {config.source}"
            raise FileNotFoundError(msg)

        image = _rng.choice(images)
        logger.info("displaying %s", image)
        show(image)
        await sleep(config.interval)


async def main(config: DirDaemonConfig) -> None:
    """Run the directory slideshow daemon with the real hardware display."""

    def _show(path: Path) -> None:
        show_image(path, dither=config.dither)

    await run_dir_daemon(config, show=_show)
