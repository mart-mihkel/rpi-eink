"""Tests for the image-to-panel-BMP conversion script."""

from typing import TYPE_CHECKING

from PIL import Image

from eink.scripts.convert import (
    _fit_to_panel,
    _nearest_panel_color,
    _panel_colors,
    convert,
)

if TYPE_CHECKING:
    from pathlib import Path

_width = 800
_height = 480


def test_fit_to_panel_crops_a_wider_image_to_exact_size() -> None:
    """A source wider than the panel's aspect ratio is cropped down to exact size."""
    image = Image.new("RGB", (1600, 400))

    fitted = _fit_to_panel(image, _width, _height)

    assert fitted.size == (_width, _height)


def test_fit_to_panel_crops_a_taller_image_to_exact_size() -> None:
    """A source taller than the panel's aspect ratio is cropped down to exact size."""
    image = Image.new("RGB", (800, 1200))

    fitted = _fit_to_panel(image, _width, _height)

    assert fitted.size == (_width, _height)


def test_fit_to_panel_keeps_an_already_exact_size_image() -> None:
    """A source that already matches the panel's resolution is left as-is."""
    image = Image.new("RGB", (_width, _height))

    fitted = _fit_to_panel(image, _width, _height)

    assert fitted.size == (_width, _height)


def test_nearest_panel_color_keeps_an_exact_match() -> None:
    """A pixel that's already a real panel color maps to itself."""
    for color in _panel_colors:
        assert _nearest_panel_color(color) == color


def test_nearest_panel_color_maps_pure_red_to_the_real_ink_red() -> None:
    """An idealized pure color maps to the closest real ink color, not itself."""
    assert _nearest_panel_color((255, 0, 0)) == (191, 0, 0)


def test_convert_writes_a_panel_sized_bmp_using_only_real_ink_colors(
    tmp_path: Path,
) -> None:
    """The output BMP is fit to the panel and uses only its 6 real ink colors."""
    source = tmp_path / "source.png"
    destination = tmp_path / "destination.bmp"
    Image.new("RGB", (1600, 400), (255, 0, 0)).save(source)

    convert(source, destination).unwrap()

    with Image.open(destination) as result:
        assert result.size == (_width, _height)
        assert set(result.get_flattened_data()) <= set(_panel_colors)


def test_convert_dither_writes_a_panel_sized_bmp_using_only_real_ink_colors(
    tmp_path: Path,
) -> None:
    """Dithering also fits the panel and stays within the 6 real ink colors."""
    source = tmp_path / "source.png"
    destination = tmp_path / "destination.bmp"
    _make_gradient(_width, _height).save(source)

    convert(source, destination, dither=True).unwrap()

    with Image.open(destination) as result:
        assert result.size == (_width, _height)
        assert set(result.get_flattened_data()) <= set(_panel_colors)


def test_convert_dither_differs_from_flat_mapping_on_a_gradient(
    tmp_path: Path,
) -> None:
    """Dithering diffuses quantization error, so it picks different pixels than flat."""
    source = tmp_path / "source.png"
    flat_destination = tmp_path / "flat.bmp"
    dithered_destination = tmp_path / "dithered.bmp"
    _make_gradient(_width, _height).save(source)

    convert(source, flat_destination).unwrap()
    convert(source, dithered_destination, dither=True).unwrap()

    with (
        Image.open(flat_destination) as flat,
        Image.open(dithered_destination) as dithered,
    ):
        assert list(flat.get_flattened_data()) != list(dithered.get_flattened_data())


def test_convert_dither_matches_flat_mapping_on_a_solid_color(tmp_path: Path) -> None:
    """A solid color has no quantization error to diffuse, so both modes agree."""
    source = tmp_path / "source.png"
    flat_destination = tmp_path / "flat.bmp"
    dithered_destination = tmp_path / "dithered.bmp"
    Image.new("RGB", (_width, _height), (255, 0, 0)).save(source)

    convert(source, flat_destination).unwrap()
    convert(source, dithered_destination, dither=True).unwrap()

    with (
        Image.open(flat_destination) as flat,
        Image.open(dithered_destination) as dithered,
    ):
        assert list(flat.get_flattened_data()) == list(dithered.get_flattened_data())


def _make_gradient(width: int, height: int) -> Image.Image:
    """Build a horizontal black-to-white gradient, which flat mapping visibly bands."""
    image = Image.new("RGB", (width, height))
    for x in range(width):
        value = round(255 * x / (width - 1))
        for y in range(height):
            image.putpixel((x, y), (value, value, value))
    return image
