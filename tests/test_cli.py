"""Tests for the CLI commands."""

from typer.testing import CliRunner

from flow.cli import app


runner = CliRunner()


def test_version():
    """Test --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_help():
    """Test --help flag."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.stdout
    assert "review" in result.stdout
    assert "scaffold" in result.stdout


def test_config_path():
    """Test config path command."""
    result = runner.invoke(app, ["config", "path"])
    assert result.exit_code == 0
    assert "config.toml" in result.stdout
