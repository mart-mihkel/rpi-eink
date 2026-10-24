"""Tests for preparing images for the e-Paper panel."""

from typing import TYPE_CHECKING

from PIL import Image

from eink.scripts.display import prepare_image

if TYPE_CHECKING:
    from pathlib import Path

_PANEL_SIZE = (800, 480)
"""Resolution the converter fits non-BMP images to."""

_SOURCE_SIZE = (320, 240)
"""Resolution of a source image that already fits the panel's aspect ratio."""


def test_prepare_image_keeps_bmp_dimensions(tmp_path: Path) -> None:
    """A BMP is panel-ready, so its dimensions are left untouched."""
    path = tmp_path / "panel.bmp"
    Image.new("RGB", _SOURCE_SIZE).save(path)

    prepared = prepare_image(path)

    assert prepared.size == _SOURCE_SIZE


def test_prepare_image_keeps_uppercase_bmp_dimensions(tmp_path: Path) -> None:
    """The BMP check is case-insensitive."""
    path = tmp_path / "panel.BMP"
    Image.new("RGB", _SOURCE_SIZE).save(path, format="BMP")

    prepared = prepare_image(path)

    assert prepared.size == _SOURCE_SIZE


def test_prepare_image_fits_non_bmp_to_panel(tmp_path: Path) -> None:
    """A non-BMP source is converted and fitted to the panel."""
    path = tmp_path / "photo.png"
    Image.new("RGB", (1600, 400), (255, 0, 0)).save(path)

    prepared = prepare_image(path)

    assert prepared.size == _PANEL_SIZE


def test_prepare_image_forwards_dither_flag(tmp_path: Path) -> None:
    """Dithering is applied only when requested."""
    path = tmp_path / "gradient.png"
    Image.linear_gradient("L").convert("RGB").save(path)

    flat = prepare_image(path, dither=False)
    dithered = prepare_image(path, dither=True)

    assert flat.tobytes() != dithered.tobytes()
