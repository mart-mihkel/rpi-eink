"""Smoke tests for the Typer command-line interface."""

from typer.testing import CliRunner

from eink.main import app

_USAGE_ERROR = 2
"""Exit code for CLI usage errors."""

runner = CliRunner()


def test_app_help_lists_commands() -> None:
    """Top-level help advertises every subcommand."""
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in ("render", "update", "daemon", "demo", "convert", "display"):
        assert command in result.output


def test_daemon_help_shows_schedule_options() -> None:
    """The daemon command documents its intervals and flags."""
    result = runner.invoke(app, ["daemon", "--help"])

    assert result.exit_code == 0
    assert "--interval" in result.output
    assert "--retry-interval" in result.output
    assert "--dither" in result.output
    assert "--log-level" in result.output


def test_daemon_rejects_non_positive_intervals() -> None:
    """Non-positive schedules fail with a usage error, not a traceback."""
    for args in (
        ["daemon", "--interval", "0"],
        ["daemon", "--retry-interval", "-5"],
    ):
        result = runner.invoke(app, args)

        assert result.exit_code == _USAGE_ERROR
        assert "must be positive" in result.output


def test_convert_rejects_missing_source() -> None:
    """A nonexistent source image fails with a usage error."""
    result = runner.invoke(app, ["convert", "does-not-exist.png"])

    assert result.exit_code == _USAGE_ERROR
