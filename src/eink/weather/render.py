"""Render Open-Meteo data with a Jinja-templated SVG."""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

import cairosvg
from jinja2 import Environment, PackageLoader, StrictUndefined
from PIL.Image import Image
from PIL.Image import open as image_open
from returns.result import safe

from eink.weather.schemas import ForecastContext, RenderContext, WeatherCode

if TYPE_CHECKING:
    from eink.weather.schemas import (
        DailyForecast,
        WeatherKind,
        WeatherResponse,
    )


class WeatherRenderer:
    """Render weather responses as dashboard SVGs and e-Paper images."""

    _weather_kinds: ClassVar[dict[WeatherCode, WeatherKind]] = {
        WeatherCode.CLEAR_SKY: "clear",
        WeatherCode.MAINLY_CLEAR: "partly-cloudy",
        WeatherCode.PARTLY_CLOUDY: "partly-cloudy",
        WeatherCode.OVERCAST: "cloudy",
        WeatherCode.FOG: "fog",
        WeatherCode.DEPOSITING_RIME_FOG: "fog",
        WeatherCode.THUNDERSTORM: "thunderstorm",
        WeatherCode.THUNDERSTORM_LIGHT_HAIL: "thunderstorm",
        WeatherCode.THUNDERSTORM_HEAVY_HAIL: "thunderstorm",
    }

    _weather_labels: ClassVar[dict[WeatherKind, str]] = {
        "clear": "Clear",
        "partly-cloudy": "Partly cloudy",
        "cloudy": "Cloudy",
        "fog": "Fog",
        "rain": "Rain",
        "snow": "Snow",
        "thunderstorm": "Thunderstorm",
    }

    _width: int = 800
    _height: int = 480
    _forecast_days: int = 7

    def __init__(self) -> None:
        """Initialize a renderer for a dashboard panel."""
        self._template_env = Environment(
            loader=PackageLoader("eink.weather", "templates"),
            autoescape=True,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @staticmethod
    def weather_kind(code: WeatherCode) -> WeatherKind:
        """Map an Open-Meteo WMO weather code to an icon category."""
        exact_kind = WeatherRenderer._weather_kinds.get(code)
        if exact_kind is not None:
            return exact_kind

        if WeatherCode.DRIZZLE_LIGHT <= code <= WeatherCode.FREEZING_RAIN_HEAVY:
            return "rain"

        if WeatherCode.RAIN_SHOWERS_SLIGHT <= code <= WeatherCode.RAIN_SHOWERS_VIOLENT:
            return "rain"

        if WeatherCode.SNOW_SLIGHT <= code <= WeatherCode.SNOW_HEAVY:
            return "snow"

        if WeatherCode.SNOW_SHOWERS_SLIGHT <= code <= WeatherCode.SNOW_SHOWERS_HEAVY:
            return "snow"

        return "cloudy"

    @staticmethod
    def weather_label(code: WeatherCode) -> str:
        """Return a short human-readable label for a WMO weather code."""
        return WeatherRenderer._weather_labels[WeatherRenderer.weather_kind(code)]

    def render_svg(self, weather: WeatherResponse) -> str:
        """Render weather data as SVG text using the dashboard template."""
        context = self._render_context(weather)
        template = self._template_env.get_template("dashboard.svg.jinja")
        return template.render(context)

    @safe
    def render(self, weather: WeatherResponse) -> Image:
        """Render weather data as an RGB image sized for the e-Paper panel."""
        svg = self.render_svg(weather)
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=self._width,
            output_height=self._height,
        )

        with image_open(BytesIO(png)) as image:
            return image.convert("RGB")

    def _render_context(self, weather: WeatherResponse) -> RenderContext:
        """Convert the API model into values needed by the SVG template."""
        current = weather.current
        daily = weather.daily
        sunrise = "—"
        sunset = "—"
        forecast: list[ForecastContext] = []

        if daily is not None:
            sunrise = daily.sunrise[0].strftime("%H:%M")
            sunset = daily.sunset[0].strftime("%H:%M")
            forecast = self._forecast_context(daily)

        return RenderContext(
            location_name="Tartu",
            updated=current.time.strftime("%a %d %b · %H:%M"),
            temperature=self._temperature(
                current.temperature_2m,
                weather.current_units.temperature_2m,
            ),
            condition=self.weather_label(current.weather_code),
            kind=self.weather_kind(current.weather_code),
            apparent=self._temperature(
                current.apparent_temperature,
                weather.current_units.temperature_2m,
            ),
            humidity=f"{current.relative_humidity_2m:.0f}%",
            wind=self._with_unit(
                current.wind_speed_10m,
                weather.current_units.wind_speed_10m,
            ),
            sunrise=sunrise,
            sunset=sunset,
            forecast=forecast,
        )

    def _forecast_context(self, daily: DailyForecast) -> list[ForecastContext]:
        """Convert daily API arrays into forecast-card values."""
        values = zip(
            daily.time,
            daily.weather_code,
            daily.temperature_2m_max,
            daily.temperature_2m_min,
            daily.precipitation_probability_max,
            strict=False,
        )

        return [
            ForecastContext(
                day=day.strftime("%a"),
                kind=self.weather_kind(code),
                high=f"{maximum:.0f}°",
                low=f"{minimum:.0f}°",
                precipitation=("—" if probability is None else f"{probability:.0f}%"),
            )
            for day, code, maximum, minimum, probability in list(values)[
                : self._forecast_days
            ]
        ]

    @staticmethod
    def _temperature(value: float, unit: str) -> str:
        """Format a temperature using the unit returned by the API."""
        return f"{value:.0f}{unit}"

    @staticmethod
    def _with_unit(value: float, unit: str) -> str:
        """Format a numeric weather value with its API-provided unit."""
        return f"{value:.0f} {unit}"
