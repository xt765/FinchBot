"""CLI command registration tests."""

from __future__ import annotations

from typer.testing import CliRunner

from finchbot.cli_main import app

runner = CliRunner()


def test_webhook_command_is_registered() -> None:
    """The documented `finchbot webhook` command should exist."""
    result = runner.invoke(app, ["webhook", "--help"])

    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output


def test_channel_serve_command_remains_registered() -> None:
    """The original nested command should stay available."""
    result = runner.invoke(app, ["channel", "serve", "--help"])

    assert result.exit_code == 0
    assert "--host" in result.output
    assert "--port" in result.output
