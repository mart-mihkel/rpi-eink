"""Fetch open-meteo weather data."""

from returns.future import future_safe
from returns.io import IOFailure, IOSuccess
from returns.result import Failure, Success

from eink.logging import logger
from eink.weather import OpenMeteoClient


@future_safe
async def main() -> None:
    """Fetch weather data and close the asynchronous client."""
    client = OpenMeteoClient()

    match await client.get_forecast():
        case IOSuccess(Success(forecast)):
            pass
        case IOFailure(Failure(err)):
            logger.error(err)

    match await client.get_current():
        case IOSuccess(Success(current)):
            pass
        case IOFailure(Failure(err)):
            logger.error(err)
            return

    await client.close()

    logger.info(current)
    logger.info(forecast)
