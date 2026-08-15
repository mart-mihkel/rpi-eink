"""Fetch weather data and render the dashboard image."""

from __future__ import annotations

from typing import TYPE_CHECKING

from returns.future import future_safe
from returns.unsafe import unsafe_perform_io

from eink.logging import logger
from eink.weather.client import OpenMeteoClient
from eink.weather.render import WeatherRenderer

if TYPE_CHECKING:
    from pathlib import Path


@future_safe
async def main(destination: Path) -> None:
    """Fetch the forecast and save its rendered dashboard image."""
    client = OpenMeteoClient()
    forecast = await client.get_forecast()
    weather = unsafe_perform_io(forecast.unwrap())

    await client.close()

    image = WeatherRenderer().render(weather).unwrap()
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG")
    logger.info("wrote dashboard image to %s", destination)
