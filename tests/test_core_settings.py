"""CoreSettings: precedence env > <config dir>/.env > defaults; para_root checks."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticUndefined

from para_files.core.settings import CoreSettings, config_dir_path, load_settings
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


def test_config_dir_follows_the_environment(cfg_dir):
    assert config_dir_path() == cfg_dir


def test_config_dir_defaults_to_home(tmp_path, monkeypatch):
    monkeypatch.delenv("PARA_FILES_CONFIG_DIR", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_dir_path() == tmp_path / ".config" / "para-files"


def test_env_example_matches_the_settings():
    """Every NAME=value in .env.example (commented or not) is a real setting with its default."""
    text = (Path(__file__).parent.parent / ".env.example").read_text(encoding="utf-8")
    lines = re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=(\S*)", text, flags=re.MULTILINE)
    assert lines, "no settings found in .env.example"
    key_field = CoreSettings.model_fields["openrouter_api_key"]
    key_names = set(key_field.validation_alias.choices)
    for name, value in lines:
        if name in key_names:
            continue
        assert name.startswith("PARA_FILES_"), name
        field = CoreSettings.model_fields.get(name.removeprefix("PARA_FILES_").lower())
        assert field is not None, name
        if field.default_factory is not None:
            assert Path(value).expanduser() == field.default_factory(), name
        elif field.default is not PydanticUndefined and field.default is not None:
            default = str(field.default)
            assert value == (default.lower() if isinstance(field.default, bool) else default), name
