"""Display an image on the e-Paper panel."""

from typing import TYPE_CHECKING

from PIL import Image
from returns.result import safe

from rink.convert import ImageConverter
from rink.logging import logger
from rink.vendor.epd7in3e import EPD

if TYPE_CHECKING:
    from pathlib import Path


def prepare_image(src: Path, *, dither: bool = True) -> Image.Image:
    """Load an image, fitting and quantizing non-BMP sources to the panel."""
    with Image.open(src) as image:
        if src.suffix.lower() == ".bmp":
            return image.copy()

        converter = ImageConverter()
        return converter.convert(image, dither=dither).unwrap()


def display_image(image: Image.Image) -> None:
    """Send a panel-ready image to the display, then put the panel back to sleep."""
    with EPD() as epd:
        logger.info("displaying image")
        epd.display(epd.getbuffer(image).unwrap())


@safe
def main(src: Path) -> None:
    """Show an image on the panel, then put it back to sleep."""
    display_image(prepare_image(src))
