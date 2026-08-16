"""Render Open-Meteo data with a Jinja-templated SVG."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

import cairosvg
from jinja2 import Environment, PackageLoader, StrictUndefined
from PIL.Image import Image
from PIL.Image import open as image_open
from returns.result import safe

from eink.weather.schemas import (
    ChartBar,
    ChartLabel,
    ChartPoint,
    ForecastContext,
    HourlyContext,
    RenderContext,
    WeatherCode,
)

if TYPE_CHECKING:
    from datetime import datetime

    from eink.weather.schemas import (
        DailyForecast,
        WeatherKind,
        WeatherResponse,
    )


@dataclass(frozen=True, slots=True)
class _Layout:
    """Pixel dimensions of the dashboard panel and of its hourly chart."""

    width: int = 800
    height: int = 480
    left: float = 24
    right: float = 776
    top: float = 242
    bottom: float = 278
    baseline: float = 286
    bar_width: float = 18
    bar_height: float = 36
    label_gap: float = 9
    label_inset: float = 22
    hour_baseline: float = 307
    hours: int = 24
    hour_step: int = 4
    minimum_hours: int = 2


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

    _forecast_days: int = 7

    def __init__(self) -> None:
        """Initialize a renderer for a dashboard panel."""
        self._layout = _Layout()
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
            output_width=self._layout.width,
            output_height=self._layout.height,
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
            hourly=self._hourly_context(weather),
            forecast=forecast,
        )

    def _hourly_context(self, weather: WeatherResponse) -> HourlyContext | None:
        """Convert hourly API arrays into chart geometry for the template."""
        hourly = weather.hourly
        if hourly is None:
            return None

        start = self._hourly_start(hourly.time, weather.current.time)
        end = start + self._layout.hours
        times = hourly.time[start:end]
        temperatures = hourly.temperature_2m[start:end]
        probabilities = [
            0.0 if value is None else value
            for value in hourly.precipitation_probability[start:end]
        ]

        if min(len(times), len(temperatures)) < self._layout.minimum_hours:
            return None

        step = (self._layout.right - self._layout.left) / (len(times) - 1)
        centers = [self._layout.left + index * step for index in range(len(times))]
        points = self._temperature_points(temperatures, centers)

        return HourlyContext(
            temperature=points,
            precipitation=self._precipitation_bars(probabilities, centers),
            temperature_labels=self._temperature_labels(temperatures, points),
            precipitation_labels=self._precipitation_labels(probabilities, centers),
            hours=self._hour_labels(times, centers),
        )

    @staticmethod
    def _hourly_start(times: list[datetime], current: datetime) -> int:
        """Find the index of the hour the current observation falls into."""
        hour = current.replace(minute=0, second=0, microsecond=0)
        return next((index for index, time in enumerate(times) if time >= hour), 0)

    def _temperature_points(
        self,
        temperatures: list[float],
        centers: list[float],
    ) -> list[ChartPoint]:
        """Scale temperatures into vertices of the chart's line."""
        coldest = min(temperatures)
        span = max(temperatures) - coldest
        height = self._layout.bottom - self._layout.top

        return [
            ChartPoint(
                x=round(center, 1),
                y=round(
                    self._layout.bottom
                    if span == 0
                    else self._layout.bottom - (value - coldest) / span * height,
                    1,
                ),
            )
            for value, center in zip(temperatures, centers, strict=True)
        ]

    def _precipitation_bars(
        self,
        probabilities: list[float],
        centers: list[float],
    ) -> list[ChartBar]:
        """Scale precipitation probabilities into bars rising from the axis."""
        return [
            ChartBar(
                x=round(center - self._layout.bar_width / 2, 1),
                y=round(self._layout.baseline - self._bar_height(probability), 1),
                width=self._layout.bar_width,
                height=round(self._bar_height(probability), 1),
            )
            for probability, center in zip(probabilities, centers, strict=True)
            if probability > 0
        ]

    def _temperature_labels(
        self,
        temperatures: list[float],
        points: list[ChartPoint],
    ) -> list[ChartLabel]:
        """Annotate the warmest and coldest hours of the window."""
        peaks = {
            temperatures.index(max(temperatures)),
            temperatures.index(min(temperatures)),
        }

        return [
            ChartLabel(
                x=self._label_x(points[index].x),
                y=round(points[index].y - self._layout.label_gap, 1),
                text=f"{temperatures[index]:.0f}°",
            )
            for index in sorted(peaks)
        ]

    def _precipitation_labels(
        self,
        probabilities: list[float],
        centers: list[float],
    ) -> list[ChartLabel]:
        """Annotate the wettest hour of the window, when rain is expected."""
        peak = probabilities.index(max(probabilities))
        if probabilities[peak] <= 0:
            return []

        return [
            ChartLabel(
                x=self._label_x(centers[peak]),
                y=round(
                    self._layout.baseline
                    - self._bar_height(probabilities[peak])
                    - self._layout.label_gap / 2,
                    1,
                ),
                text=f"{probabilities[peak]:.0f}%",
            )
        ]

    def _hour_labels(
        self,
        times: list[datetime],
        centers: list[float],
    ) -> list[ChartLabel]:
        """Label the time axis at a fixed hourly interval."""
        return [
            ChartLabel(
                x=self._label_x(centers[index]),
                y=self._layout.hour_baseline,
                text=times[index].strftime("%H:%M"),
            )
            for index in range(0, len(times), self._layout.hour_step)
        ]

    def _bar_height(self, probability: float) -> float:
        """Scale a precipitation probability to a bar height in pixels."""
        return probability / 100 * self._layout.bar_height

    def _label_x(self, x: float) -> float:
        """Keep a centered label inside the horizontal bounds of the chart."""
        left = self._layout.left + self._layout.label_inset
        right = self._layout.right - self._layout.label_inset
        return round(min(max(x, left), right), 1)

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
