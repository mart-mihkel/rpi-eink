"""Waveshare 7.3 inch (e) e-Paper driver."""

from enum import IntEnum
from typing import Self

from PIL import Image
from returns.result import safe

from eink.logging import logger
from eink.vendor.epdconfig import (
    Pin,
    delay_ms,
    digital_read,
    digital_write,
    module_exit,
    module_init,
    spi_writebyte,
    spi_writebytes,
)


class Command(IntEnum):
    """
    Panel command opcodes.

    Section 6 ("Command Table") of the Waveshare user manual documents only
    five opcodes: Power OFF, Power ON, Deep Sleep, Data Start transmission,
    and Data Refresh — those five are named here to match. The manual does
    not document the panel's internal register bring-up sequence, so the
    other opcodes sent via `_init_sequence` keep a `CMD_<hex>` placeholder
    name; their real meaning is proprietary to the driver IC.

    https://files.waveshare.com/wiki/7.3inch-e-Paper-HAT-(E)/7.3inch-e-Paper-(E)-user-manual.pdf
    """

    CMD_00 = 0x00
    CMD_01 = 0x01
    POWER_OFF = 0x02
    CMD_03 = 0x03
    POWER_ON = 0x04
    CMD_05 = 0x05
    CMD_06 = 0x06
    DEEP_SLEEP = 0x07
    CMD_08 = 0x08
    DATA_START_TRANSMISSION = 0x10
    DATA_REFRESH = 0x12
    CMD_30 = 0x30
    CMD_50 = 0x50
    CMD_60 = 0x60
    CMD_61 = 0x61
    CMD_84 = 0x84
    CMD_AA = 0xAA
    CMD_E3 = 0xE3


# (command, [data, ...]) pairs sent to bring up the panel's internal registers.
_init_sequence: list[tuple[Command, list[int]]] = [
    (Command.CMD_AA, [0x49, 0x55, 0x20, 0x08, 0x09, 0x18]),
    (Command.CMD_01, [0x3F]),
    (Command.CMD_00, [0x5F, 0x69]),
    (Command.CMD_03, [0x00, 0x54, 0x00, 0x44]),
    (Command.CMD_05, [0x40, 0x1F, 0x1F, 0x2C]),
    (Command.CMD_06, [0x6F, 0x1F, 0x17, 0x49]),
    (Command.CMD_08, [0x6F, 0x1F, 0x1F, 0x22]),
    (Command.CMD_30, [0x03]),
    (Command.CMD_50, [0x3F]),
    (Command.CMD_60, [0x02, 0x00]),
    (Command.CMD_61, [0x03, 0x20, 0x01, 0xE0]),
    (Command.CMD_84, [0x01]),
    (Command.CMD_E3, [0x2F]),
]


class EPD:
    """Driver for the Waveshare 7.3 inch (e) e-Paper display."""

    def __init__(self) -> None:
        """Bind the driver to its GPIO pins and default resolution."""
        self.reset_pin = Pin.RST_PIN
        self.dc_pin = Pin.DC_PIN
        self.busy_pin = Pin.BUSY_PIN
        self.cs_pin = Pin.CS_PIN
        self.width = 800
        self.height = 480

    def __enter__(self) -> Self:
        """Initialize the panel; it must not stay powered on without sleeping."""
        logger.info("init and clear")
        if self.init() != 0:
            msg = "failed to initialize the e-Paper display"
            raise RuntimeError(msg)

        return self

    def __exit__(self, *exc_info: object) -> None:
        """Put the panel back to sleep, even if the block above raised."""
        del exc_info

        logger.info("goto sleep")
        self.sleep()

    def reset(self) -> None:
        """Perform a hardware reset."""
        digital_write(self.reset_pin, 1)
        delay_ms(20)
        digital_write(self.reset_pin, 0)
        delay_ms(2)
        digital_write(self.reset_pin, 1)
        delay_ms(20)

    def send_command(self, command: Command) -> None:
        """Send a single command byte to the panel."""
        digital_write(self.dc_pin, 0)
        digital_write(self.cs_pin, 0)
        spi_writebyte([command])
        digital_write(self.cs_pin, 1)

    def send_data(self, data: int) -> None:
        """Send a single data byte to the panel."""
        digital_write(self.dc_pin, 1)
        digital_write(self.cs_pin, 0)
        spi_writebyte([data])
        digital_write(self.cs_pin, 1)

    def send_datas(self, data: list[int]) -> None:
        """Send a sequence of data bytes to the panel."""
        digital_write(self.dc_pin, 1)
        digital_write(self.cs_pin, 0)
        spi_writebytes(data)
        digital_write(self.cs_pin, 1)

    def read_busy_h(self) -> None:
        """Block until the panel reports it is idle."""
        logger.debug("e-Paper busy H")
        while digital_read(self.busy_pin) == 0:
            delay_ms(5)

        logger.debug("e-Paper busy H release")

    def turn_on_display(self) -> None:
        """Power the panel, refresh the display, then power it down."""
        self.send_command(Command.POWER_ON)
        self.read_busy_h()

        self.send_command(Command.DATA_REFRESH)
        self.send_data(0x00)
        self.read_busy_h()

        self.send_command(Command.POWER_OFF)
        self.send_data(0x00)
        self.read_busy_h()

    def init(self) -> int:
        """Initialize the SPI bus and the panel's internal registers."""
        if module_init() != 0:
            return -1

        self.reset()
        self.read_busy_h()
        delay_ms(30)

        for command, data in _init_sequence:
            self.send_command(command)
            for value in data:
                self.send_data(value)

        self.send_command(Command.POWER_ON)
        self.read_busy_h()
        return 0

    @safe
    def getbuffer(self, image: Image.Image) -> list[int]:
        """Convert an image to the panel's packed 4-bit-per-pixel buffer format."""
        # Palette with the 7 colors supported by the panel, padded to 256 entries.
        pal_image = Image.new("P", (1, 1))
        pal_image.putpalette(
            (
                0,
                0,
                0,
                255,
                255,
                255,
                255,
                255,
                0,
                255,
                0,
                0,
                0,
                0,
                0,
                0,
                0,
                255,
                0,
                255,
                0,
            )
            + (0, 0, 0) * 249,
        )

        imwidth, imheight = image.size
        if imwidth == self.width and imheight == self.height:
            image_temp = image
        elif imwidth == self.height and imheight == self.width:
            image_temp = image.rotate(90, expand=True)
        else:
            msg = (
                f"invalid image dimensions {imwidth}x{imheight}, "
                f"expected {self.width}x{self.height} or {self.height}x{self.width}"
            )
            raise ValueError(msg)

        # Convert the source image to the 7 colors, dithering if needed.
        image_7color = image_temp.convert("RGB").quantize(palette=pal_image)
        buf_7color = bytearray(image_7color.tobytes("raw"))

        # PIL does not support 4 bit color, so pack the 4 bits of color
        # into a single byte to transfer to the panel.
        buf = [0x00] * (self.width * self.height // 2)
        for idx, i in enumerate(range(0, len(buf_7color), 2)):
            buf[idx] = (buf_7color[i] << 4) + buf_7color[i + 1]

        return buf

    def display(self, image: list[int]) -> None:
        """Push a buffer produced by `getbuffer` to the panel."""
        self.send_command(Command.DATA_START_TRANSMISSION)
        self.send_datas(image)
        self.turn_on_display()

    def clear(self, color: int = 0x11) -> None:
        """Fill the panel with a single color."""
        self.send_command(Command.DATA_START_TRANSMISSION)
        self.send_datas([color] * (self.height * self.width // 2))
        self.turn_on_display()

    def sleep(self) -> None:
        """Put the panel into deep sleep and release the SPI/GPIO resources."""
        self.send_command(Command.DEEP_SLEEP)
        self.send_data(0xA5)

        delay_ms(2000)
        module_exit()
