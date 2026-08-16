"""Client and schemas for the Open-Meteo weather API."""

from httpx import AsyncClient
from returns.future import future_safe

from eink.logging import logger
from eink.weather.schemas import OpenMeteoQuery, WeatherResponse


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

    _hourly_vars: tuple[str, ...] = (
        "temperature_2m",
        "precipitation_probability",
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
            hourly=list(self._hourly_vars),
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
