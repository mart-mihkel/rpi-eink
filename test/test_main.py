"""Smoke tests for the rich-click command-line interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner
from PIL import Image

from eink.main import app

if TYPE_CHECKING:
    from pathlib import Path

_USAGE_ERROR = 2
"""Exit code for CLI usage errors."""

_PANEL_SIZE = (800, 480)
"""Resolution the converter fits every image to."""

runner = CliRunner()


def test_app_help_lists_commands() -> None:
    """Top-level help advertises every subcommand."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in (
        "weather-update",
        "weather-daemon",
        "dir-daemon",
        "demo",
        "convert",
        "display",
    ):
        assert command in result.output


def test_render_command_is_gone() -> None:
    """The removed render command is no longer registered."""
    result = runner.invoke(app, ["render"])

    assert result.exit_code == _USAGE_ERROR


def test_update_alias_is_gone() -> None:
    """The renamed update command is no longer registered under its old name."""
    result = runner.invoke(app, ["update"])

    assert result.exit_code == _USAGE_ERROR


def test_weather_daemon_help_shows_schedule_options() -> None:
    """The weather-daemon command documents its intervals and flags."""
    result = runner.invoke(app, ["weather-daemon", "--help"])

    assert result.exit_code == 0
    assert "--interval" in result.output
    assert "--retry-interval" in result.output
    assert "--dither" in result.output
    assert "--log-level" in result.output


def test_weather_daemon_rejects_non_positive_intervals() -> None:
    """Non-positive schedules fail with a usage error, not a traceback."""
    for args in (
        ["weather-daemon", "--interval", "0"],
        ["weather-daemon", "--retry-interval", "-5"],
    ):
        result = runner.invoke(app, args)

        assert result.exit_code == _USAGE_ERROR
        assert "must be positive" in result.output


def test_dir_daemon_help_shows_options() -> None:
    """The dir-daemon command documents its source and schedule options."""
    result = runner.invoke(app, ["dir-daemon", "--help"])

    assert result.exit_code == 0
    assert "--src" in result.output
    assert "--interval" in result.output
    assert "--recursive" in result.output
    assert "--seed" in result.output
    assert "--dither" in result.output
    assert "--log-level" in result.output


def test_dir_daemon_rejects_bad_schedule(tmp_path: Path) -> None:
    """Missing src and non-positive intervals fail with a usage error."""
    result = runner.invoke(app, ["dir-daemon"])
    assert result.exit_code == _USAGE_ERROR

    result = runner.invoke(
        app, ["dir-daemon", "--src", str(tmp_path), "--interval", "0"]
    )
    assert result.exit_code == _USAGE_ERROR
    assert "must be positive" in result.output

    result = runner.invoke(app, ["dir-daemon", "--src", str(tmp_path / "missing")])
    assert result.exit_code == _USAGE_ERROR
    assert "must be a directory" in result.output


def test_convert_rejects_missing_source() -> None:
    """A nonexistent source image fails with a usage error."""
    result = runner.invoke(app, ["convert", "does-not-exist.png"])

    assert result.exit_code == _USAGE_ERROR


@pytest.mark.parametrize(
    "command",
    ["weather-update", "weather-daemon", "dir-daemon", "demo", "convert", "display"],
)
def test_every_command_renders_help(command: str) -> None:
    """Each registered command renders its own help without errors."""
    result = runner.invoke(app, [command, "--help"])

    assert result.exit_code == 0
    assert f"Usage: rink {command}" in result.output


def test_convert_writes_a_panel_bmp(tmp_path: Path) -> None:
    """The convert command accepts positional paths and the negated dither flag."""
    source = tmp_path / "source.png"
    destination = tmp_path / "destination.bmp"
    Image.new("RGB", (10, 10), (255, 0, 0)).save(source)

    result = runner.invoke(
        app,
        ["convert", str(source), str(destination), "--no-dither"],
    )

    assert result.exit_code == 0
    with Image.open(destination) as converted:
        assert converted.size == _PANEL_SIZE
