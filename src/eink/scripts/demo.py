"""WaveShare vendored demo."""
import time
from enum import IntEnum

from PIL import Image, ImageDraw, ImageFont
from returns.result import safe

from eink.constants import DATA
from eink.logging import logger
from eink.vendor.epd7in3e import EPD


class _Colors(IntEnum):
    """Colors for the Waveshare 7.3 inch (e) e-Paper display."""

    BLACK = 0x000000
    WHITE = 0xFFFFFF
    YELLOW = 0x00FFFF
    RED = 0x0000FF
    BLUE = 0xFF0000
    GREEN = 0x00FF00


@safe
def main() -> None:
    """Draw shapes and a bitmap on the panel, then put it to sleep."""
    with EPD() as epd:
        epd.clear()

        font24 = ImageFont.truetype(str(DATA / "Font.ttc"), 24)
        font18 = ImageFont.truetype(str(DATA / "Font.ttc"), 18)
        font40 = ImageFont.truetype(str(DATA / "Font.ttc"), 40)

        logger.info("drawing on the image")
        h_image = Image.new("RGB", (epd.width, epd.height), _Colors.WHITE)
        draw = ImageDraw.Draw(h_image)
        draw.text((5, 0), "hello world", font=font18, fill=_Colors.RED)
        draw.text((5, 20), "7.3inch e-Paper (e)", font=font24, fill=_Colors.YELLOW)
        draw.text((5, 45), "微雪电子", font=font40, fill=_Colors.GREEN)
        draw.text((5, 85), "微雪电子", font=font40, fill=_Colors.BLUE)
        draw.text((5, 125), "微雪电子", font=font40, fill=_Colors.BLACK)

        draw.line((5, 170, 80, 245), fill=_Colors.BLUE)
        draw.line((80, 170, 5, 245), fill=_Colors.YELLOW)
        draw.rectangle((5, 170, 80, 245), outline=_Colors.BLACK)
        draw.rectangle((90, 170, 165, 245), fill=_Colors.GREEN)
        draw.arc((5, 250, 80, 325), 0, 360, fill=_Colors.RED)
        draw.chord((90, 250, 165, 325), 0, 360, fill=_Colors.YELLOW)
        epd.display(epd.getbuffer(h_image).unwrap())
        time.sleep(3)

        logger.info("read bmp file")
        bmp_image = Image.open(DATA / "7in3e.bmp")
        epd.display(epd.getbuffer(bmp_image).unwrap())
        time.sleep(3)

        logger.info("clear")
        epd.clear()
