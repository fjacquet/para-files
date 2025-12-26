"""Tests for the main module."""

from __future__ import annotations

from typer.testing import CliRunner

from para_files import __version__
from para_files.main import app


runner = CliRunner()


def test_version():
    """Verify package version is set."""
    assert __version__ == "0.1.0"


def test_main_help():
    """Verify main function shows help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "para-files" in result.output.lower()
    assert "classify" in result.output
    assert "move" in result.output


def test_main_version():
    """Verify version flag works."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_classify_missing_path():
    """Verify classify command errors on missing file path."""
    result = runner.invoke(app, ["classify"])
    # Should fail because no file path provided
    assert result.exit_code == 2
    assert "missing argument" in result.output.lower()


def test_classify_nonexistent_file():
    """Verify classify command warns on nonexistent file.

    With multi-file support, the command continues with warnings
    instead of failing on individual missing files.
    """
    result = runner.invoke(app, ["classify", "/nonexistent/file.txt"])
    # Should succeed but with warning (no files to process)
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "warning" in result.output.lower()


def test_move_missing_path():
    """Verify move command errors on missing file path."""
    result = runner.invoke(app, ["move"])
    # Should fail because no file path provided
    assert result.exit_code == 2
    assert "missing argument" in result.output.lower()


def test_move_nonexistent_file():
    """Verify move command warns on nonexistent file.

    With multi-file support, the command continues with warnings
    instead of failing on individual missing files.
    """
    result = runner.invoke(app, ["move", "/nonexistent/file.txt", "--dry-run"])
    # Should succeed but with warning (no files to process)
    assert result.exit_code == 0
    assert "not found" in result.output.lower() or "warning" in result.output.lower()


def test_move_help():
    """Verify move command help."""
    result = runner.invoke(app, ["move", "--help"])
    assert result.exit_code == 0
    assert "dry-run" in result.output
    assert "copy" in result.output
    assert "conflict" in result.output


def test_config_path():
    """Verify config command shows path."""
    result = runner.invoke(app, ["config", "--path"])
    assert result.exit_code == 0
    assert "config.toml" in result.output
    assert "Exists:" in result.output


def test_config_show():
    """Verify config command shows configuration."""
    result = runner.invoke(app, ["config", "--show"])
    assert result.exit_code == 0
    assert "para_root" in result.output
    assert "mlx" in result.output
    assert "llm" in result.output
