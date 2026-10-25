"""Rich logging setup."""

import logging
import sys
from typing import TextIO

import rich.traceback
from rich.console import Console
from rich.logging import RichHandler

logger = logging.getLogger("rink")
"""Project logger."""


def rich_handler(stream: TextIO) -> RichHandler:
    """Build a rich handler writing to a stream."""
    return RichHandler(
        console=Console(file=stream),
        rich_tracebacks=True,
        omit_repeated_times=False,
    )


def setup_logging() -> None:
    """Install the rich log handler and rich tracebacks."""
    root = logging.getLogger()
    if not any(isinstance(handler, RichHandler) for handler in root.handlers):
        root.addHandler(rich_handler(sys.stderr))

    rich.traceback.install(suppress=[rich])
    logger.setLevel(logging.INFO)
