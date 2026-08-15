"""Fetch, render, convert, and display the weather dashboard."""

from __future__ import annotations

from returns.future import future_safe
from returns.unsafe import unsafe_perform_io

from eink.constants import DATA
from eink.convert import ImageConverter
from eink.scripts.display import main as display
from eink.weather.client import OpenMeteoClient
from eink.weather.render import WeatherRenderer


@future_safe
async def main(*, dither: bool = True) -> None:
    """Fetch weather, render a PNG, convert it to BMP, and display it."""
    client = OpenMeteoClient()
    forecast = await client.get_forecast()
    weather = unsafe_perform_io(forecast.unwrap())

    await client.close()

    img = WeatherRenderer().render(weather).unwrap()
    img = ImageConverter().convert(img, dither=dither).unwrap()

    display_path = DATA / "display.bmp"
    display_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(display_path, format="BMP")
    display(display_path).unwrap()
