"""Tests for scaffold command."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from flow.cli import app


runner = CliRunner()


def test_scaffold_cli():
    """Test scaffolding a CLI project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["scaffold", "cli", "test-cli", "-o", tmpdir])
        assert result.exit_code == 0

        project_dir = Path(tmpdir) / "test-cli"
        assert project_dir.exists()
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "src" / "test_cli" / "__init__.py").exists()
        assert (project_dir / "src" / "test_cli" / "cli.py").exists()


def test_scaffold_api():
    """Test scaffolding an API project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["scaffold", "api", "test-api", "-o", tmpdir])
        assert result.exit_code == 0

        project_dir = Path(tmpdir) / "test-api"
        assert project_dir.exists()
        assert (project_dir / "src" / "test_api" / "main.py").exists()
        assert (project_dir / "src" / "test_api" / "routes.py").exists()


def test_scaffold_library():
    """Test scaffolding a library project."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(app, ["scaffold", "library", "test-lib", "-o", tmpdir])
        assert result.exit_code == 0

        project_dir = Path(tmpdir) / "test-lib"
        assert project_dir.exists()
        assert (project_dir / "src" / "test_lib" / "core.py").exists()
