"""Tests for the image-to-panel-BMP converter."""

from PIL import Image

from eink.convert import ImageConverter

_width = 800
_height = 480


def test_fit_to_panel_crops_a_wider_image_to_exact_size() -> None:
    """A source wider than the panel's aspect ratio is cropped down to exact size."""
    image = Image.new("RGB", (1600, 400))

    fitted = ImageConverter(width=_width, height=_height)._fit_to_panel(image)

    assert fitted.size == (_width, _height)


def test_fit_to_panel_crops_a_taller_image_to_exact_size() -> None:
    """A source taller than the panel's aspect ratio is cropped down to exact size."""
    image = Image.new("RGB", (800, 1200))

    fitted = ImageConverter(width=_width, height=_height)._fit_to_panel(image)

    assert fitted.size == (_width, _height)


def test_fit_to_panel_keeps_an_already_exact_size_image() -> None:
    """A source that already matches the panel's resolution is left as-is."""
    image = Image.new("RGB", (_width, _height))

    fitted = ImageConverter(width=_width, height=_height)._fit_to_panel(image)

    assert fitted.size == (_width, _height)


def test_nearest_panel_color_keeps_an_exact_match() -> None:
    """A pixel that's already a real panel color maps to itself."""
    for color in ImageConverter._panel_colors:
        assert ImageConverter._nearest_panel_color(color) == color


def test_nearest_panel_color_maps_pure_red_to_the_real_ink_red() -> None:
    """An idealized pure color maps to the closest real ink color, not itself."""
    assert ImageConverter._nearest_panel_color((255, 0, 0)) == (191, 0, 0)


def test_convert_returns_a_panel_sized_image_using_only_real_ink_colors() -> None:
    """The output image is fit to the panel and uses only its 6 real ink colors."""
    source = Image.new("RGB", (1600, 400), (255, 0, 0))

    result = ImageConverter(width=_width, height=_height).convert(source).unwrap()

    assert result.size == (_width, _height)
    assert set(result.get_flattened_data()) <= set(ImageConverter._panel_colors)


def test_convert_dither_returns_an_image_using_only_real_ink_colors() -> None:
    """Dithering also fits to the panel and stays within the 6 real ink colors."""
    source = _make_gradient(_width, _height)

    result = (
        ImageConverter(width=_width, height=_height)
        .convert(
            source,
            dither=True,
        )
        .unwrap()
    )

    assert result.size == (_width, _height)
    assert set(result.get_flattened_data()) <= set(ImageConverter._panel_colors)


def test_convert_dither_differs_from_flat_mapping_on_a_gradient() -> None:
    """Dithering diffuses quantization error, so it picks different pixels than flat."""
    source = _make_gradient(_width, _height)
    converter = ImageConverter(width=_width, height=_height)

    flat = converter.convert(source).unwrap()
    dithered = converter.convert(source, dither=True).unwrap()

    assert list(flat.get_flattened_data()) != list(dithered.get_flattened_data())


def test_convert_dither_matches_flat_mapping_on_a_solid_color() -> None:
    """A solid color has no quantization error to diffuse, so both modes agree."""
    source = Image.new("RGB", (_width, _height), (255, 0, 0))
    converter = ImageConverter(width=_width, height=_height)

    flat = converter.convert(source).unwrap()
    dithered = converter.convert(source, dither=True).unwrap()

    assert list(flat.get_flattened_data()) == list(dithered.get_flattened_data())


def _make_gradient(width: int, height: int) -> Image.Image:
    """Build a horizontal black-to-white gradient, which flat mapping visibly bands."""
    image = Image.new("RGB", (width, height))
    for x in range(width):
        value = round(255 * x / (width - 1))
        for y in range(height):
            image.putpixel((x, y), (value, value, value))
    return image
