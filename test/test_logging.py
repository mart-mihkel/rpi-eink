"""Tests for the rich logging setup."""

import logging

from rich.logging import RichHandler

from rink.logging import logger, setup_logging


def test_setup_logging_is_idempotent() -> None:
    """Repeated setup keeps exactly one rich handler on the root logger."""
    root = logging.getLogger()
    before = list(root.handlers)

    try:
        setup_logging()
        setup_logging()

        rich_handlers = [
            handler for handler in root.handlers if isinstance(handler, RichHandler)
        ]
        assert len(rich_handlers) == 1
    finally:
        for handler in list(root.handlers):
            if handler not in before:
                root.removeHandler(handler)


def test_setup_logging_defaults_to_info() -> None:
    """The project logger starts at info after setup."""
    previous = logger.level
    try:
        setup_logging()
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(previous)
