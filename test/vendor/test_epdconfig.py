"""Tests for the vendored epdconfig hardware interface."""

import time
from typing import TYPE_CHECKING

import pytest

from eink.vendor import epdconfig
from eink.vendor.epdconfig import Pin

if TYPE_CHECKING:
    from .conftest import Hardware


@pytest.mark.parametrize("pin", [Pin.RST_PIN, Pin.DC_PIN, Pin.PWR_PIN])
def test_digital_write_and_read_round_trip(hardware: Hardware, pin: Pin) -> None:
    """Writing an output pin high or low is reflected back by reading it."""
    del hardware

    epdconfig.digital_write(pin, 1)
    assert epdconfig.digital_read(pin) is True

    epdconfig.digital_write(pin, 0)
    assert epdconfig.digital_read(pin) is False


def test_digital_write_unknown_pin_is_a_noop(hardware: Hardware) -> None:
    """Writing a pin with no wired GPIO device does nothing, and does not raise."""
    del hardware

    epdconfig.digital_write(Pin.CS_PIN, 1)


def test_digital_read_unknown_pin_returns_false(hardware: Hardware) -> None:
    """Reading a pin with no wired GPIO device reports low."""
    del hardware

    assert epdconfig.digital_read(Pin.CS_PIN) is False


def test_digital_read_busy_pin_reflects_panel_state(hardware: Hardware) -> None:
    """The busy pin reads the panel's simulated idle/busy signal."""
    hardware.pins.pin(Pin.BUSY_PIN).drive_low()
    assert epdconfig.digital_read(Pin.BUSY_PIN) is False

    hardware.pins.pin(Pin.BUSY_PIN).drive_high()
    assert epdconfig.digital_read(Pin.BUSY_PIN) is True


def test_delay_ms_sleeps_the_given_milliseconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Delaying converts milliseconds to seconds before sleeping."""
    slept = []
    monkeypatch.setattr(time, "sleep", slept.append)

    epdconfig.delay_ms(20)

    assert slept == [0.02]


def test_spi_writebyte_and_writebyte2(hardware: Hardware) -> None:
    """Single and multi-byte SPI writes are forwarded to the SPI device."""
    epdconfig.spi_writebyte([0x12])
    hardware.spi.writebytes.assert_called_once_with([0x12])

    epdconfig.spi_writebytes([0x01, 0x02])
    hardware.spi.writebytes2.assert_called_once_with([0x01, 0x02])


def test_module_init_powers_on_and_opens_spi(hardware: Hardware) -> None:
    """Initializing the module turns on power and configures the SPI bus."""
    expected_spi_speed_hz = 4_000_000
    assert epdconfig.module_init() == 0

    assert epdconfig.digital_read(Pin.PWR_PIN) is True
    hardware.spi.open.assert_called_once_with(0, 0)
    assert hardware.spi.max_speed_hz == expected_spi_speed_hz
    assert hardware.spi.mode == 0b00


def test_module_exit_powers_off_and_closes_spi(hardware: Hardware) -> None:
    """Exiting the module turns off all output pins and closes the SPI bus."""
    epdconfig.module_init()

    epdconfig.module_exit()

    assert epdconfig.digital_read(Pin.PWR_PIN) is False
    assert epdconfig.digital_read(Pin.RST_PIN) is False
    assert epdconfig.digital_read(Pin.DC_PIN) is False
    hardware.spi.close.assert_called_once()


def test_module_exit_cleanup_releases_gpio_pins(hardware: Hardware) -> None:
    """Exiting with cleanup also releases the underlying GPIO devices."""
    del hardware

    epdconfig.module_init()

    epdconfig.module_exit(cleanup=True)

    assert epdconfig._rst_pin().closed
    assert epdconfig._dc_pin().closed
    assert epdconfig._pwr_pin().closed
    assert epdconfig._busy_pin().closed
