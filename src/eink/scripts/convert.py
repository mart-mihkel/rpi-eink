"""Convert an arbitrary image into a panel-ready BMP."""

from typing import TYPE_CHECKING, cast

from PIL import Image
from returns.result import safe

from eink.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

_panel_colors: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (255, 255, 255),
    (255, 243, 56),
    (191, 0, 0),
    (100, 64, 255),
    (67, 138, 28),
)


def _fit_to_panel(image: Image.Image, width: int, height: int) -> Image.Image:
    """Resize `image` to cover width x height, then center-crop the overhang."""
    scale = max(width / image.width, height / image.height)
    resized_size = (round(image.width * scale), round(image.height * scale))
    logger.debug("resizing %s to %s (scale=%.3f)", image.size, resized_size, scale)
    resized = image.resize(resized_size, Image.Resampling.LANCZOS)

    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    logger.debug(
        "center-cropping to %sx%s at offset (%s, %s)",
        width,
        height,
        left,
        top,
    )

    return resized.crop((left, top, left + width, top + height))


def _nearest_panel_color(pixel: tuple[int, int, int]) -> tuple[int, int, int]:
    """Find the panel color closest to `pixel` in RGB space (no dithering)."""
    red, green, blue = pixel
    return min(
        _panel_colors,
        key=lambda color: (
            (color[0] - red) ** 2 + (color[1] - green) ** 2 + (color[2] - blue) ** 2
        ),
    )


def _quantize_flat(image: Image.Image) -> Image.Image:
    """Map every pixel to the nearest panel color, with no dithering."""
    rgb_pixels = cast("tuple[tuple[int, int, int], ...]", image.get_flattened_data())
    quantized = Image.new("RGB", image.size)
    quantized.putdata([_nearest_panel_color(pixel) for pixel in rgb_pixels])
    return quantized


def _quantize_dithered(image: Image.Image) -> Image.Image:
    """Map every pixel to the nearest panel color, using Floyd-Steinberg dithering."""
    palette_image = Image.new("P", (1, 1))
    flat_palette = [channel for color in _panel_colors for channel in color]
    palette_image.putpalette(flat_palette)
    quantized = image.quantize(
        palette=palette_image,
        dither=Image.Dither.FLOYDSTEINBERG,
    )

    return quantized.convert("RGB")


@safe
def convert(
    src: Path,
    dest: Path,
    *,
    width: int = 800,
    height: int = 480,
    dither: bool = False,
) -> None:
    """Fit `source` to the panel and quantize it to the panel's real ink colors."""
    logger.info("loading %s", src)
    image = Image.open(src).convert("RGB")

    logger.info("fitting to %sx%s", width, height)
    fitted = _fit_to_panel(image, width, height)

    logger.info("quantizing to the panel's 6 ink colors (dither=%s)", dither)
    quantized = _quantize_dithered(fitted) if dither else _quantize_flat(fitted)

    logger.info("writing %s", dest)
    quantized.save(dest, format="BMP")
