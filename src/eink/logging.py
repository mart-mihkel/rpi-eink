"""Rich-backed logging setup."""

import logging
from typing import TYPE_CHECKING, Literal

import click
import rich.traceback
from click import Context, HelpFormatter, style
from rich.logging import RichHandler

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger("eink")
"""Global logger."""


def setup_logging(log_level: Literal["debug", "info", "warning", "error"]) -> None:
    """Install the rich log handler, ascii tqdm bars, and rich tracebacks."""
    logging.basicConfig(
        format="%(message)s",
        handlers=[RichHandler(show_path=False, show_time=False)],
    )

    logger.setLevel(log_level.upper())
    logger.debug("finished logging setup")

    rich.traceback.install(suppress=[rich, click])
    logger.debug("finished rich tracebacks setup")


class _ColorHelpFormatter(HelpFormatter):
    """Help formatter that colors headings, usage, and option/command names."""

    def write_usage(self, prog: str, args: str = "", prefix: str | None = None) -> None:
        prefix = prefix if prefix is not None else "Usage: "
        colored_prefix = style(prefix, fg="green", bold=True)
        super().write_usage(prog, args, prefix=colored_prefix)

    def write_heading(self, heading: str) -> None:
        super().write_heading(style(heading, fg="yellow", bold=True))

    def write_dl(
        self,
        rows: Iterable[tuple[str, str]],
        col_max: int = 30,
        col_spacing: int = 2,
    ) -> None:
        super().write_dl(
            [(style(name, fg="cyan"), description) for name, description in rows],
            col_max=col_max,
            col_spacing=col_spacing,
        )


Context.formatter_class = _ColorHelpFormatter
