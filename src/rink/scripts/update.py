"""Fetch, render, convert, and display the weather dashboard."""

from __future__ import annotations

from rink.constants import DATA
from rink.convert import ImageConverter
from rink.results import asafe
from rink.scripts.display import main as display
from rink.weather.client import OpenMeteoClient
from rink.weather.render import WeatherRenderer


@asafe
async def main(*, dither: bool = True) -> None:
    """Fetch weather, render a PNG, convert it to BMP, and display it."""
    client = OpenMeteoClient()
    try:
        weather = (await client.get_forecast()).unwrap()
    finally:
        await client.close()

    img = WeatherRenderer().render(weather).unwrap()
    img = ImageConverter().convert(img, dither=dither).unwrap()

    display_path = DATA / "display.bmp"
    display_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(display_path, format="BMP")
    display(display_path).unwrap()
