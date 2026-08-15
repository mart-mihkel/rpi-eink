"""Tests for the Open-Meteo client."""

from typing import TYPE_CHECKING

import pytest
from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success

from eink.weather import OpenMeteoClient, WeatherResponse

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@pytest.fixture
def anyio_backend() -> str:
    """Restrict anyio-marked tests to the asyncio backend."""
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[OpenMeteoClient]:
    """Provide an OpenMeteoClient, closing its HTTP client afterwards."""
    client = OpenMeteoClient()
    yield client
    await client.close()


@pytest.mark.vcr
async def test_get_current_default_location(client: OpenMeteoClient) -> None:
    """Fetch current conditions for the client's default coordinates."""
    result = await client.get_current().awaitable()

    match result:
        case IOSuccess(Success(weather)):
            assert isinstance(weather, WeatherResponse)
            assert weather.daily is None
            assert weather.daily_units is None
        case _:
            pytest.fail(f"expected success, got {result!r}")


@pytest.mark.vcr
async def test_get_current_explicit_location(client: OpenMeteoClient) -> None:
    """Fetch current conditions for an explicit latitude and longitude."""
    result = await client.get_current(latitude=51.5072, longitude=-0.1276).awaitable()

    match result:
        case IOSuccess(Success(weather)):
            assert weather.latitude == pytest.approx(51.5072, abs=0.2)
            assert weather.longitude == pytest.approx(-0.1276, abs=0.2)
        case _:
            pytest.fail(f"expected success, got {result!r}")


@pytest.mark.vcr
async def test_get_forecast_default_days(client: OpenMeteoClient) -> None:
    """Fetch a forecast using the default seven-day window."""
    forecast_days = 7
    result = await client.get_forecast().awaitable()

    match result:
        case IOSuccess(Success(weather)):
            assert weather.daily is not None
            assert len(weather.daily.time) == forecast_days
        case _:
            pytest.fail(f"expected success, got {result!r}")


@pytest.mark.vcr
async def test_get_forecast_custom_days(client: OpenMeteoClient) -> None:
    """Fetch a forecast for a caller-specified number of days."""
    forecast_days = 3
    result = await client.get_forecast(forecast_days=forecast_days).awaitable()

    match result:
        case IOSuccess(Success(weather)):
            assert weather.daily is not None
            assert len(weather.daily.time) == forecast_days
        case _:
            pytest.fail(f"expected success, got {result!r}")


async def test_get_current_invalid_latitude_is_a_failure(
    client: OpenMeteoClient,
) -> None:
    """Reject an out-of-range latitude without making a request."""
    result = await client.get_current(latitude=200, longitude=26.7290).awaitable()

    match result:
        case IOFailure(Failure(err)):
            assert isinstance(err, ValueError)
        case _:
            pytest.fail(f"expected failure, got {result!r}")
