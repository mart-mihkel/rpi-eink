"""Client and schemas for the Open-Meteo weather API."""

from datetime import date, datetime
from enum import IntEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

type WeatherKind = Literal[
    "clear",
    "partly-cloudy",
    "cloudy",
    "fog",
    "rain",
    "snow",
    "thunderstorm",
]


class WeatherCode(IntEnum):
    """WMO weather interpretation codes returned by Open-Meteo."""

    CLEAR_SKY = 0
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3
    FOG = 45
    DEPOSITING_RIME_FOG = 48
    DRIZZLE_LIGHT = 51
    DRIZZLE_MODERATE = 53
    DRIZZLE_DENSE = 55
    FREEZING_DRIZZLE_LIGHT = 56
    FREEZING_DRIZZLE_DENSE = 57
    RAIN_SLIGHT = 61
    RAIN_MODERATE = 63
    RAIN_HEAVY = 65
    FREEZING_RAIN_LIGHT = 66
    FREEZING_RAIN_HEAVY = 67
    SNOW_SLIGHT = 71
    SNOW_MODERATE = 73
    SNOW_HEAVY = 75
    SNOW_GRAINS = 77
    RAIN_SHOWERS_SLIGHT = 80
    RAIN_SHOWERS_MODERATE = 81
    RAIN_SHOWERS_VIOLENT = 82
    SNOW_SHOWERS_SLIGHT = 85
    SNOW_SHOWERS_HEAVY = 86
    THUNDERSTORM = 95
    THUNDERSTORM_LIGHT_HAIL = 96
    THUNDERSTORM_HEAVY_HAIL = 99


class OpenMeteoQuery(BaseModel):
    """Validated query parameters for the Open-Meteo forecast endpoint."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    current: list[str] = Field(min_length=1)
    hourly: list[str] | None = None
    daily: list[str] | None = None
    forecast_days: int | None = Field(default=None, ge=1, le=16)
    timezone: str = "auto"


class CurrentWeatherUnits(BaseModel):
    """Units returned for current weather values."""

    model_config = ConfigDict(extra="forbid")

    time: str
    interval: str
    temperature_2m: str
    relative_humidity_2m: str
    apparent_temperature: str
    weather_code: str
    wind_speed_10m: str


class CurrentWeather(BaseModel):
    """Current weather conditions for a location."""

    model_config = ConfigDict(extra="forbid")

    time: datetime
    interval: int
    temperature_2m: float
    relative_humidity_2m: float
    apparent_temperature: float
    weather_code: WeatherCode
    wind_speed_10m: float


class HourlyForecastUnits(BaseModel):
    """Units returned for hourly forecast values."""

    model_config = ConfigDict(extra="forbid")

    time: str
    temperature_2m: str
    precipitation_probability: str


class HourlyForecast(BaseModel):
    """Hourly weather forecast for a location."""

    model_config = ConfigDict(extra="forbid")

    time: list[datetime]
    temperature_2m: list[float]
    precipitation_probability: list[float | None]


class DailyForecastUnits(BaseModel):
    """Units returned for daily forecast values."""

    model_config = ConfigDict(extra="forbid")

    time: str
    weather_code: str
    temperature_2m_max: str
    temperature_2m_min: str
    precipitation_probability_max: str
    sunrise: str
    sunset: str


class DailyForecast(BaseModel):
    """Daily weather forecast for a location."""

    model_config = ConfigDict(extra="forbid")

    time: list[date]
    weather_code: list[WeatherCode]
    temperature_2m_max: list[float]
    temperature_2m_min: list[float]
    precipitation_probability_max: list[float | None]
    sunrise: list[datetime]
    sunset: list[datetime]


class WeatherResponse(BaseModel):
    """Validated weather response from Open-Meteo."""

    model_config = ConfigDict(extra="forbid")

    latitude: float
    longitude: float
    generationtime_ms: float
    utc_offset_seconds: int
    timezone: str
    timezone_abbreviation: str
    elevation: float
    current_units: CurrentWeatherUnits
    current: CurrentWeather
    hourly_units: HourlyForecastUnits | None = None
    hourly: HourlyForecast | None = None
    daily_units: DailyForecastUnits | None = None
    daily: DailyForecast | None = None


class ForecastContext(BaseModel):
    """Values rendered by one forecast card."""

    day: str
    kind: WeatherKind
    high: str
    low: str
    precipitation: str


class ChartPoint(BaseModel):
    """One vertex of the hourly temperature line."""

    x: float
    y: float


class ChartBar(BaseModel):
    """One precipitation-probability bar of the hourly chart."""

    x: float
    y: float
    width: float
    height: float


class ChartLabel(BaseModel):
    """A positioned text label of the hourly chart."""

    x: float
    y: float
    text: str


class HourlyContext(BaseModel):
    """Chart geometry rendered for the next hours of the forecast."""

    temperature: list[ChartPoint]
    precipitation: list[ChartBar]
    temperature_labels: list[ChartLabel]
    precipitation_labels: list[ChartLabel]
    hours: list[ChartLabel]


class RenderContext(BaseModel):
    """Values passed to the dashboard SVG template."""

    location_name: str
    updated: str
    temperature: str
    condition: str
    kind: WeatherKind
    apparent: str
    humidity: str
    wind: str
    sunrise: str
    sunset: str
    hourly: HourlyContext | None
    forecast: list[ForecastContext]
