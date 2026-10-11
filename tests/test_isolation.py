"""Test isolation: no test may read the owner's real configuration or PARA volume."""

from __future__ import annotations

import os
import pwd
from pathlib import Path

from para_files.core.settings import config_dir_path, load_settings


def _real_home() -> Path:
    """The account's real home directory, independent of the HOME the fixture sets."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def test_config_dir_is_sandboxed() -> None:
    """The personal config dir resolves inside the per-test HOME, never the owner's."""
    assert not config_dir_path().is_relative_to(_real_home())
    assert config_dir_path().is_relative_to(Path(os.environ["HOME"]))


def test_no_para_files_variable_or_key_leaks_in() -> None:
    leaked = [name for name in os.environ if name.startswith("PARA_FILES_")]
    assert leaked in ([], ["PARA_FILES_CONFIG_DIR"])
    assert "OPENROUTER_API_KEY" not in os.environ


def test_a_dotenv_in_the_working_directory_is_never_read(tmp_path: Path) -> None:
    """Only <config dir>/.env is read; a .env in the cwd (tmp_path) is ignored."""
    root = tmp_path / "PARA"
    (root / "0_Inbox").mkdir(parents=True)
    (tmp_path / ".env").write_text("PARA_FILES_MAX_WORKERS=9\n")
    assert load_settings(para_root=root).max_workers == 4
