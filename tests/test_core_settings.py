"""CoreSettings: precedence env > <config dir>/.env > defaults; para_root checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from para_files.core.settings import load_settings
from tests.core_helpers import make_para_root


@pytest.fixture
def cfg_dir(tmp_path, monkeypatch):
    path = tmp_path / "cfg"
    path.mkdir()
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(path))
    return path


def test_dotenv_in_config_dir_is_read(tmp_path, cfg_dir):
    root = make_para_root(tmp_path)
    (cfg_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=2\n")
    settings = load_settings()
    assert settings.para_root == root
    assert settings.max_workers == 2


def test_environment_beats_dotenv(tmp_path, cfg_dir, monkeypatch):
    root = make_para_root(tmp_path)
    (cfg_dir / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=2\n")
    monkeypatch.setenv("PARA_FILES_MAX_WORKERS", "3")
    assert load_settings().max_workers == 3


def test_overrides_beat_environment(tmp_path, cfg_dir, monkeypatch):
    monkeypatch.setenv("PARA_FILES_MAX_WORKERS", "3")
    assert load_settings(para_root=make_para_root(tmp_path), max_workers=5).max_workers == 5


def test_working_directory_dotenv_is_ignored(tmp_path, cfg_dir, monkeypatch):
    root = make_para_root(tmp_path)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / ".env").write_text("PARA_FILES_MAX_WORKERS=7\n")
    monkeypatch.chdir(cwd)
    assert load_settings(para_root=root).max_workers == 4


def test_root_pointing_at_a_bucket_is_refused(tmp_path, cfg_dir):
    root = make_para_root(tmp_path)
    with pytest.raises(ValidationError, match="PARA_FILES_PARA_ROOT"):
        load_settings(para_root=root / "0_Inbox")


def test_root_without_inbox_is_refused(tmp_path, cfg_dir):
    with pytest.raises(ValidationError, match="no 0_Inbox"):
        load_settings(para_root=tmp_path)


def test_openrouter_key_from_its_usual_variable(tmp_path, cfg_dir, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-value")
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.openrouter_api_key is not None
    assert settings.openrouter_api_key.get_secret_value() == "sk-test-value"
    assert "sk-test-value" not in repr(settings)


def test_cache_and_state_default_under_home(tmp_path, cfg_dir):
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.cache_path == Path.home() / ".cache" / "para-files" / "cache.sqlite"
    assert settings.state_dir == Path.home() / ".local" / "state" / "para-files"


def test_defaults(tmp_path, cfg_dir):
    settings = load_settings(para_root=make_para_root(tmp_path))
    assert settings.fallback_model == "google/gemini-3.8-flash"
    assert settings.fallback_backup_model == "anthropic/claude-sonnet-5.5"
    assert settings.calibration_min == 100
    assert settings.preview_chars == 2000


def test_config_dir_follows_the_environment(tmp_path, monkeypatch):
    from para_files.core.settings import config_dir_path
    from para_files.core.tree import config_dir

    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(tmp_path / "cfg"))
    assert config_dir_path() == tmp_path / "cfg" == config_dir()


def test_config_dir_defaults_to_home(tmp_path, monkeypatch):
    from para_files.core.settings import config_dir_path

    monkeypatch.delenv("PARA_FILES_CONFIG_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_dir_path() == tmp_path / ".config" / "para-files"


def test_settings_read_the_env_file_in_the_config_dir(tmp_path, monkeypatch):
    from para_files.core.settings import load_settings

    root = tmp_path / "PARA"
    (root / "0_Inbox").mkdir(parents=True)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".env").write_text(f"PARA_FILES_PARA_ROOT={root}\nPARA_FILES_MAX_WORKERS=7\n")
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(cfg))
    settings = load_settings()
    assert settings.para_root == root
    assert settings.max_workers == 7
