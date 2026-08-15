"""Hardware underlying interface for the Waveshare e-Paper HAT on a Raspberry Pi."""

import time
from enum import IntEnum
from functools import cache
from typing import TYPE_CHECKING

import gpiozero
import spidev

from eink.logging import logger

if TYPE_CHECKING:
    from collections.abc import Callable


class Pin(IntEnum):
    """GPIO pin numbers for the e-Paper HAT."""

    RST_PIN = 17
    DC_PIN = 25
    CS_PIN = 8
    BUSY_PIN = 24
    PWR_PIN = 18
    MOSI_PIN = 10
    SCLK_PIN = 11


@cache
def _spi() -> spidev.SpiDev:
    return spidev.SpiDev()


@cache
def _rst_pin() -> gpiozero.LED:
    return gpiozero.LED(Pin.RST_PIN)


@cache
def _dc_pin() -> gpiozero.LED:
    return gpiozero.LED(Pin.DC_PIN)


@cache
def _pwr_pin() -> gpiozero.LED:
    return gpiozero.LED(Pin.PWR_PIN)


@cache
def _busy_pin() -> gpiozero.Button:
    return gpiozero.Button(Pin.BUSY_PIN, pull_up=False)


_output_pin_factories: dict[int, Callable[[], gpiozero.LED]] = {
    Pin.RST_PIN: _rst_pin,
    Pin.DC_PIN: _dc_pin,
    Pin.PWR_PIN: _pwr_pin,
}


def digital_write(pin: int, value: int) -> None:
    """Drive the given GPIO output pin high or low."""
    factory = _output_pin_factories.get(pin)
    if factory is None:
        return

    led = factory()
    if value:
        led.on()
    else:
        led.off()


def digital_read(pin: int) -> bool:
    """Read the given GPIO pin's digital value."""
    if pin == Pin.BUSY_PIN:
        return bool(_busy_pin().value)

    factory = _output_pin_factories.get(pin)
    return bool(factory().value) if factory is not None else False


def delay_ms(delay_time: float) -> None:
    """Sleep for the given number of milliseconds."""
    time.sleep(delay_time / 1000.0)


def spi_writebyte(data: list[int]) -> None:
    """Write a single byte over SPI."""
    _spi().writebytes(data)


def spi_writebytes(data: list[int]) -> None:
    """Write a sequence of bytes over SPI."""
    _spi().writebytes2(data)


def module_init() -> int:
    """Power on the display and open the SPI bus."""
    _pwr_pin().on()

    spi = _spi()
    spi.open(0, 0)
    spi.max_speed_hz = 4_000_000
    spi.mode = 0b00
    return 0


def module_exit(*, cleanup: bool = False) -> None:
    """Power off the display and release the GPIO pins if cleaning up."""
    logger.debug("spi end")
    _spi().close()

    _rst_pin().off()
    _dc_pin().off()
    _pwr_pin().off()
    logger.debug("close 5V, module enters 0 power consumption")

    if cleanup:
        _rst_pin().close()
        _dc_pin().close()
        _pwr_pin().close()
        _busy_pin().close()
