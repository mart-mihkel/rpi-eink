"""Rich-backed logging setup."""

import logging
from typing import TYPE_CHECKING

import rich.traceback
from rich.logging import RichHandler

if TYPE_CHECKING:
    from eink.types import LogLevel

logger = logging.getLogger("eink")
"""Project logger."""


def setup_logging(log_level: LogLevel) -> None:
    """Install the rich log handler, ascii tqdm bars, and rich tracebacks."""
    logging.basicConfig(
        format="%(message)s",
        handlers=[RichHandler(show_path=False, show_time=False)],
    )

    logger.setLevel(log_level.upper())
    logger.debug("finished logging setup")

    rich.traceback.install(suppress=[rich])
    logger.debug("finished rich tracebacks setup")
