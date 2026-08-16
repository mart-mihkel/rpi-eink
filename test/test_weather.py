"""Tests for the Open-Meteo client."""

from typing import TYPE_CHECKING

import pytest
from PIL import Image
from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success

from eink.weather.client import OpenMeteoClient
from eink.weather.render import WeatherRenderer
from eink.weather.schemas import WeatherResponse

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


@pytest.fixture
async def forecast(client: OpenMeteoClient) -> WeatherResponse:
    """Fetch a forecast from the cassette recording."""
    result = await client.get_forecast().awaitable()

    match result:
        case IOSuccess(Success(weather)):
            return weather
        case _:
            pytest.fail(f"expected success, got {result!r}")


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


@pytest.mark.vcr
@pytest.mark.default_cassette("test_get_forecast_default_days")
async def test_render_svg_uses_the_jinja_template(forecast: WeatherResponse) -> None:
    """The rendered document contains the cassette data and forecast cards."""
    renderer = WeatherRenderer()
    svg = renderer.render_svg(forecast)

    assert "Tartu" in svg
    assert "7-DAY FORECAST" in svg
    assert svg.count('class="') == 0


@pytest.mark.vcr
@pytest.mark.default_cassette("test_get_forecast_default_days")
async def test_render_svg_charts_the_hourly_forecast(forecast: WeatherResponse) -> None:
    """The chart plots a full day of hourly values starting at the current hour."""
    chart_hours = 24
    renderer = WeatherRenderer()
    svg = renderer.render_svg(forecast)
    vertices = svg.split('points="')[1].split('"')[0].split()

    assert forecast.hourly is not None
    assert len(vertices) == chart_hours
    assert forecast.current.time.strftime("%H:00") in svg
    assert "unavailable" not in svg


@pytest.mark.vcr
@pytest.mark.default_cassette("test_get_forecast_default_days")
async def test_render_dashboard_returns_panel_sized_rgb_image(
    forecast: WeatherResponse,
) -> None:
    """CairoSVG rasterizes cassette data to the panel dimensions."""
    renderer = WeatherRenderer()
    result = renderer.render(forecast)

    assert isinstance(result, Success)
    image = result.unwrap()
    assert image.size == (800, 480)
    assert image.mode == "RGB"
    assert isinstance(image, Image.Image)


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
