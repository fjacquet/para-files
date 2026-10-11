"""The CLI app: --version, help without arguments, the entry point."""

from __future__ import annotations

import tomllib
from pathlib import Path

from typer.testing import CliRunner

from para_files import __version__
from para_files.cli import app


runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"para-files {__version__}"


def test_no_arguments_shows_help():
    result = runner.invoke(app, [])
    assert "Usage" in result.output


def test_missing_para_root_is_a_readable_error():
    result = runner.invoke(app, ["tree"])
    assert result.exit_code == 2
    assert "PARA_FILES_PARA_ROOT" in result.output


def test_exactly_the_six_commands():
    names = sorted(command.name for command in app.registered_commands)
    assert names == ["clean", "explain", "init", "sort", "tree", "undo"]


def test_entry_point_targets_the_new_app():
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    scripts = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]["scripts"]
    assert scripts == {"para-files": "para_files.cli.app:app"}
