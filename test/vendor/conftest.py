"""Fake GPIO/SPI backends for testing the vendored hardware driver."""

import time
from typing import TYPE_CHECKING, NamedTuple
from unittest.mock import MagicMock

import pytest
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from eink.vendor import epdconfig

if TYPE_CHECKING:
    from collections.abc import Iterator

_factories = (
    epdconfig._spi,
    epdconfig._rst_pin,
    epdconfig._dc_pin,
    epdconfig._pwr_pin,
    epdconfig._busy_pin,
)


class Hardware(NamedTuple):
    """Fake GPIO/SPI backends installed for a test."""

    pins: MockFactory
    spi: MagicMock


@pytest.fixture
def hardware(monkeypatch: pytest.MonkeyPatch) -> Iterator[Hardware]:
    """
    Back GPIO access with gpiozero's MockFactory and stub out spidev.

    The busy pin is driven high (idle) by default so `read_busy_h()` doesn't
    spin forever waiting for a real panel that isn't there.
    """
    pin_factory = MockFactory()
    Device.pin_factory = pin_factory

    spi = MagicMock()
    monkeypatch.setattr("spidev.SpiDev", MagicMock(return_value=spi))
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)

    epdconfig._busy_pin()
    pin_factory.pin(epdconfig.Pin.BUSY_PIN).drive_high()

    yield Hardware(pins=pin_factory, spi=spi)

    for factory in _factories:
        factory().close()
        factory.cache_clear()

    pin_factory.reset()
    pin_factory.close()
    Device.pin_factory = None
