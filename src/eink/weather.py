"""Client and schemas for the Open-Meteo weather API."""

from datetime import date, datetime

from httpx import AsyncClient
from pydantic import BaseModel, ConfigDict, Field
from returns.future import future_safe

from eink.logging import logger


class OpenMeteoQuery(BaseModel):
    """Validated query parameters for the Open-Meteo forecast endpoint."""

    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    current: list[str] = Field(min_length=1)
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
    weather_code: int
    wind_speed_10m: float


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
    weather_code: list[int]
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
    daily_units: DailyForecastUnits | None = None
    daily: DailyForecast | None = None


class OpenMeteoClient:
    """Retrieve and validate weather data from Open-Meteo."""

    _latitude: float = 58.3776
    _longitude: float = 26.7290
    _forecast_days: int = 7

    _current_vars: tuple[str, ...] = (
        "temperature_2m",
        "relative_humidity_2m",
        "apparent_temperature",
        "weather_code",
        "wind_speed_10m",
    )

    _daily_vars: tuple[str, ...] = (
        "weather_code",
        "temperature_2m_max",
        "temperature_2m_min",
        "precipitation_probability_max",
        "sunrise",
        "sunset",
    )

    def __init__(self) -> None:
        """Initialize the client."""
        logger.debug("initializing open-meteo client")
        self._client = AsyncClient(
            base_url="https://api.open-meteo.com/v1",
            headers={"Accept": "application/json"},
            timeout=10,
        )

    @future_safe
    async def get_current(
        self,
        latitude: float = _latitude,
        longitude: float = _longitude,
    ) -> WeatherResponse:
        """Get validated current weather conditions for a latitude and longitude."""
        logger.info(
            "fetching current weather for latitude=%s longitude=%s",
            latitude,
            longitude,
        )

        query = OpenMeteoQuery(
            latitude=latitude,
            longitude=longitude,
            current=list(self._current_vars),
        )

        logger.debug("requesting open-meteo data")
        response = await self._client.get(
            "/forecast",
            params=query.model_dump(exclude_none=True),
        )

        logger.debug("open-meteo response status=%s", response.status_code)
        response.raise_for_status()

        weather = WeatherResponse.model_validate_json(response.content)
        logger.debug(
            "received weather data for latitude=%s longitude=%s",
            weather.latitude,
            weather.longitude,
        )

        return weather

    @future_safe
    async def get_forecast(
        self,
        latitude: float = _latitude,
        longitude: float = _longitude,
        forecast_days: int = _forecast_days,
    ) -> WeatherResponse:
        """Get validated current conditions and a daily forecast."""
        logger.info(
            "fetching %s-day forecast for latitude=%s longitude=%s",
            forecast_days,
            latitude,
            longitude,
        )

        query = OpenMeteoQuery(
            latitude=latitude,
            longitude=longitude,
            current=list(self._current_vars),
            daily=list(self._daily_vars),
            forecast_days=forecast_days,
        )

        logger.debug("requesting open-meteo data")
        response = await self._client.get(
            "/forecast",
            params=query.model_dump(exclude_none=True),
        )

        logger.debug("open-meteo response status=%s", response.status_code)
        response.raise_for_status()

        weather = WeatherResponse.model_validate_json(response.content)
        logger.debug(
            "received weather data for latitude=%s longitude=%s",
            weather.latitude,
            weather.longitude,
        )

        return weather

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        logger.debug("closing open-meteo client")
        await self._client.aclose()
