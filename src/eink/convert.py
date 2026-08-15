"""Convert images for the e-Paper panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, cast

from PIL import Image
from returns.result import safe

from eink.logging import logger

if TYPE_CHECKING:
    from collections.abc import Iterable


class ImageConverter:
    """Fit and quantize images to the e-Paper panel's dimensions and colors."""

    _panel_colors: ClassVar[tuple[tuple[int, int, int], ...]] = (
        (0, 0, 0),
        (255, 255, 255),
        (255, 243, 56),
        (191, 0, 0),
        (100, 64, 255),
        (67, 138, 28),
    )

    def __init__(self, *, width: int = 800, height: int = 480) -> None:
        """Initialize a converter for a panel size."""
        self._width = width
        self._height = height

    @safe
    def convert(self, image: Image.Image, *, dither: bool = False) -> Image.Image:
        """Fit an image to the panel and quantize it to the real ink colors."""
        logger.info("fitting %s to %sx%s", image.size, self._width, self._height)
        fitted = self._fit_to_panel(image.convert("RGB"))

        logger.info("quantizing to the panel's 6 ink colors (dither=%s)", dither)
        if dither:
            return self._quantize_dithered(fitted)
        return self._quantize_flat(fitted)

    def _fit_to_panel(self, image: Image.Image) -> Image.Image:
        """Resize an image to cover the panel, then center-crop the overhang."""
        scale = max(self._width / image.width, self._height / image.height)
        resized_size = (round(image.width * scale), round(image.height * scale))
        logger.debug("resizing %s to %s (scale=%.3f)", image.size, resized_size, scale)
        resized = image.resize(resized_size, Image.Resampling.LANCZOS)

        left = (resized.width - self._width) // 2
        top = (resized.height - self._height) // 2
        logger.debug(
            "center-cropping to %sx%s at offset (%s, %s)",
            self._width,
            self._height,
            left,
            top,
        )

        return resized.crop(
            (left, top, left + self._width, top + self._height),
        )

    @classmethod
    def _nearest_panel_color(cls, pixel: tuple[int, int, int]) -> tuple[int, int, int]:
        """Find the panel color closest to a pixel in RGB space."""
        red, green, blue = pixel
        return min(
            cls._panel_colors,
            key=lambda color: (
                (color[0] - red) ** 2 + (color[1] - green) ** 2 + (color[2] - blue) ** 2
            ),
        )

    @classmethod
    def _quantize_flat(cls, image: Image.Image) -> Image.Image:
        """Map every pixel to the nearest panel color, with no dithering."""
        rgb_pixels = cast("Iterable[tuple[int, int, int]]", image.get_flattened_data())
        quantized = Image.new("RGB", image.size)
        quantized.putdata([cls._nearest_panel_color(pixel) for pixel in rgb_pixels])
        return quantized

    @classmethod
    def _quantize_dithered(cls, image: Image.Image) -> Image.Image:
        """Map every pixel to the nearest panel color using dithering."""
        palette_image = Image.new("P", (1, 1))
        flat_palette = [channel for color in cls._panel_colors for channel in color]
        palette_image.putpalette(flat_palette)
        quantized = image.quantize(
            palette=palette_image,
            dither=Image.Dither.FLOYDSTEINBERG,
        )

        return quantized.convert("RGB")
