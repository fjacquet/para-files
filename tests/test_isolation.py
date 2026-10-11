"""Test isolation: no test may read the owner's real PARA configuration."""

from __future__ import annotations

import os
import pwd
from pathlib import Path

import pytest

from para_files.config import load_config


FIXTURE_TREE = Path(__file__).parent / "fixtures" / "test_reference_tree.yaml"


def _real_home() -> Path:
    """The account's real home directory, independent of the HOME the fixture sets."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def test_para_root_is_sandboxed() -> None:
    """para_root resolves inside the per-test HOME, never the owner's volume."""
    para_root = load_config().para_root

    assert not para_root.is_relative_to(_real_home())
    assert not str(para_root).startswith("/Volumes")
    assert para_root.is_relative_to(Path(os.environ["HOME"]))


def test_reference_tree_is_fixture() -> None:
    """The reference tree is the sanitized fixture, not the personal tree."""
    assert load_config().reference_tree_path == FIXTURE_TREE


def test_dotenv_files_are_ignored(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A .env in the working directory or the config directory is never read."""
    leaked = "/should/not/load"
    config_dir = tmp_path / "config-dir"
    config_dir.mkdir()
    (config_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={leaked}\n")
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(config_dir))

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    (work_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={leaked}\n")
    monkeypatch.chdir(work_dir)

    assert load_config().para_root != Path(leaked)
