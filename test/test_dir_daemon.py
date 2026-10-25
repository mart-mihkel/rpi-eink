"""Tests for the directory slideshow daemon."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

import pytest
from PIL import Image

from rink.scripts.slideshow import (
    SUPPORTED_SUFFIXES,
    DirDaemonConfig,
    list_images,
    run_dir_daemon,
    show_image,
)

if TYPE_CHECKING:
    from pathlib import Path


class _StopError(Exception):
    """Break the daemon's infinite loop once the test has seen enough."""


_BAD_IMAGE_MESSAGE = "bad image"
_NUM_SHOWS = 3
_PANEL_SIZE = (800, 480)
"""Resolution a non-BMP source is fitted to."""


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake")
    return path


def test_dir_daemon_config_rejects_non_positive_interval(tmp_path: Path) -> None:
    """Schedules must wait a positive amount of time."""
    with pytest.raises(ValueError, match="must be positive"):
        DirDaemonConfig(source=tmp_path, interval=0.0)


def test_list_images_rejects_non_directory(tmp_path: Path) -> None:
    """A file source fails fast instead of silently showing nothing."""
    missing = tmp_path / "does-not-exist"
    with pytest.raises(NotADirectoryError, match="must be a directory"):
        list_images(missing, recursive=False)


def test_list_images_returns_sorted_supported_images(tmp_path: Path) -> None:
    """Every Pillow-readable image is picked up, in sorted order."""
    _touch(tmp_path / "b.bmp")
    _touch(tmp_path / "a.bmp")
    _touch(tmp_path / "notes.txt")
    _touch(tmp_path / "photo.JPG")
    _touch(tmp_path / "photo.png")

    assert list_images(tmp_path, recursive=False) == [
        tmp_path / "a.bmp",
        tmp_path / "b.bmp",
        tmp_path / "photo.JPG",
        tmp_path / "photo.png",
    ]


def test_supported_suffixes_match_pillow_readable_formats() -> None:
    """The slideshow accepts what Pillow can open and nothing else."""
    assert {".bmp", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif"} <= set(
        SUPPORTED_SUFFIXES,
    )
    assert ".txt" not in SUPPORTED_SUFFIXES
    assert ".pdf" not in SUPPORTED_SUFFIXES


def test_list_images_recursive_searches_subdirectories(tmp_path: Path) -> None:
    """Recursive mode finds nested images; flat mode ignores them."""
    _touch(tmp_path / "top.bmp")
    _touch(tmp_path / "sub" / "nested.bmp")
    _touch(tmp_path / "sub" / "notes.txt")

    assert list_images(tmp_path, recursive=False) == [tmp_path / "top.bmp"]
    assert list_images(tmp_path, recursive=True) == [
        tmp_path / "sub" / "nested.bmp",
        tmp_path / "top.bmp",
    ]


async def test_run_dir_daemon_exits_when_empty(tmp_path: Path) -> None:
    """An empty source stops the daemon with an error instead of looping."""
    config = DirDaemonConfig(source=tmp_path, interval=1.0)

    with pytest.raises(FileNotFoundError, match="no images found"):
        await run_dir_daemon(config, show=lambda _path: None)


async def test_run_dir_daemon_shows_random_images_then_sleeps(
    tmp_path: Path,
) -> None:
    """Each tick shows one image and waits the full interval."""
    images = [tmp_path / name for name in ("a.bmp", "b.bmp", "c.bmp")]
    for path in images:
        _touch(path)
    config = DirDaemonConfig(source=tmp_path, interval=600.0, seed=42)
    shown: list[Path] = []
    delays: list[float] = []
    expected_rng = random.Random(42)  # noqa: S311 - deterministic test order, not cryptographic
    expected = [expected_rng.choice(sorted(images)) for _ in range(_NUM_SHOWS)]

    def _show(path: Path) -> None:
        shown.append(path)
        if len(shown) >= _NUM_SHOWS:
            raise _StopError

    async def _sleep(delay: float) -> None:
        delays.append(delay)

    with pytest.raises(_StopError):
        await run_dir_daemon(config, show=_show, sleep=_sleep)

    assert shown == expected
    assert delays == [config.interval] * 2


async def test_run_dir_daemon_propagates_show_failures(tmp_path: Path) -> None:
    """A bad image stops the daemon with an error instead of being skipped."""
    _touch(tmp_path / "a.bmp")
    config = DirDaemonConfig(source=tmp_path, interval=600.0)

    def _show(_path: Path) -> None:
        msg = _BAD_IMAGE_MESSAGE
        raise ValueError(msg)

    with pytest.raises(ValueError, match=_BAD_IMAGE_MESSAGE):
        await run_dir_daemon(config, show=_show)


def test_show_image_converts_non_bmp_in_memory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PNG reaches the panel fitted to it, with no intermediate BMP written."""
    path = tmp_path / "photo.png"
    Image.new("RGB", (1600, 400), (255, 0, 0)).save(path)
    shown: list[Image.Image] = []
    monkeypatch.setattr("rink.scripts.slideshow.display_image", shown.append)

    show_image(path)

    assert [image.size for image in shown] == [_PANEL_SIZE]
    assert [item.name for item in tmp_path.iterdir()] == ["photo.png"]


def test_show_image_passes_bmp_through(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A BMP is already panel-ready, so it is displayed unchanged."""
    path = tmp_path / "panel.bmp"
    Image.new("RGB", (320, 240)).save(path)
    shown: list[Image.Image] = []
    monkeypatch.setattr("rink.scripts.slideshow.display_image", shown.append)

    show_image(path)

    assert [image.size for image in shown] == [(320, 240)]
