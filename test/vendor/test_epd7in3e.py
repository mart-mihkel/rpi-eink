"""Tests for the vendored EPD driver."""

from typing import TYPE_CHECKING

import pytest
from PIL import Image
from returns.result import Failure

from eink.vendor.epd7in3e import EPD
from eink.vendor.epdconfig import Pin

if TYPE_CHECKING:
    from .conftest import Hardware


def test_getbuffer_packs_a_solid_native_size_image() -> None:
    """A native-orientation solid image quantizes to a single packed byte value."""
    white_byte = 0x11
    epd = EPD()
    image = Image.new("RGB", (epd.width, epd.height), (255, 255, 255))

    buf = epd.getbuffer(image).unwrap()

    assert len(buf) == epd.width * epd.height // 2
    assert set(buf) == {white_byte}


def test_getbuffer_rotates_a_swapped_dimension_image() -> None:
    """A portrait/landscape-swapped image is rotated before packing."""
    red_byte = 0x33
    epd = EPD()
    image = Image.new("RGB", (epd.height, epd.width), (255, 0, 0))

    buf = epd.getbuffer(image).unwrap()

    assert len(buf) == epd.width * epd.height // 2
    assert set(buf) == {red_byte}


def test_getbuffer_rejects_mismatched_dimensions() -> None:
    """Mismatched image dimensions are a Failure, instead of corrupting the output."""
    epd = EPD()
    image = Image.new("RGB", (100, 100), (0, 255, 0))

    result = epd.getbuffer(image)

    assert isinstance(result, Failure)
    assert isinstance(result.failure(), str)
    assert "invalid image dimensions" in str(result.failure())


def test_context_manager_initializes_and_sleeps(hardware: Hardware) -> None:
    """Entering initializes the panel; exiting puts it back to sleep."""
    with EPD() as epd:
        assert isinstance(epd, EPD)
        hardware.spi.close.assert_not_called()

    hardware.spi.close.assert_called_once()
    assert hardware.pins.pin(Pin.PWR_PIN).state is False


def test_context_manager_sleeps_even_if_the_block_raises(hardware: Hardware) -> None:
    """The panel must go to sleep even when the block raises, or it stays powered on."""
    msg = "boom"

    with pytest.raises(RuntimeError, match=msg), EPD():
        raise RuntimeError(msg)

    hardware.spi.close.assert_called_once()
    assert hardware.pins.pin(Pin.PWR_PIN).state is False
