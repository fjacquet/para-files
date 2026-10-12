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


def test_importing_the_cli_loads_neither_the_old_pipeline_nor_litellm():
    import subprocess
    import sys

    code = (
        "import para_files.cli, sys; "
        "print('para_files.pipeline' in sys.modules, 'litellm' in sys.modules)"
    )
    out = subprocess.run(  # noqa: S603 - runs this interpreter on a fixed snippet
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.split() == ["False", "False"]


import sys  # noqa: E402

import pytest  # noqa: E402
from loguru import logger  # noqa: E402

from para_files.cli.app import configure_logging  # noqa: E402


@pytest.fixture
def restore_logger():
    yield
    logger.remove()
    logger.add(sys.__stderr__)


def test_logging_is_quiet_by_default(capsys, restore_logger):
    configure_logging(verbose=False)
    logger.debug("debug line")
    logger.warning("warning line")
    err = capsys.readouterr().err
    assert "debug line" not in err
    assert "warning line" in err


def test_verbose_shows_debug(capsys, restore_logger):
    configure_logging(verbose=True)
    logger.debug("debug line")
    assert "debug line" in capsys.readouterr().err


def test_verbose_option_is_accepted():
    from typer.testing import CliRunner

    from para_files.cli import app

    result = CliRunner().invoke(app, ["-v", "--version"])
    assert result.exit_code == 0, result.output
