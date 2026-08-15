"""Display an image on the e-Paper panel."""

from typing import TYPE_CHECKING

from PIL import Image
from returns.result import safe

from eink.logging import logger
from eink.vendor.epd7in3e import EPD

if TYPE_CHECKING:
    from pathlib import Path


@safe
def display(path: Path) -> None:
    """Show the image at `path` on the panel, then put it back to sleep."""
    logger.info("loading %s", path)
    image = Image.open(path)

    with EPD() as epd:
        logger.info("displaying image")
        epd.display(epd.getbuffer(image).unwrap())
