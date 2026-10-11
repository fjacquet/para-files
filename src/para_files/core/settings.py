"""Settings of the new core (spec §4.1, settings precedence).

Sources, highest first: init arguments, environment variables, ``<config dir>/.env``,
defaults. There is no YAML source and no working-directory ``.env``, so the result does not
depend on where a command runs.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


INBOX = "0_Inbox"
BUCKET_NAME = re.compile(r"^[0-4]_")


def in_dot_folder(path: Path, root: Path) -> bool:
    """True when path is inside root and some part below root starts with a dot."""
    resolved, base = path.resolve(), root.resolve()
    if not resolved.is_relative_to(base):
        return False
    return any(part.startswith(".") for part in resolved.relative_to(base).parts)


def _home(*parts: str) -> Path:
    return Path.home().joinpath(*parts)


def config_dir_path() -> Path:
    """Personal config directory: $PARA_FILES_CONFIG_DIR if set, else ~/.config/para-files."""
    override = os.environ.get("PARA_FILES_CONFIG_DIR")
    return Path(override).expanduser() if override else Path.home() / ".config" / "para-files"


class PathSettings(BaseSettings):
    """The two paths ``init`` needs before the PARA root has an inbox: no root check."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    para_root: Path | None = None
    state_dir: Path = Field(default_factory=lambda: _home(".local", "state", "para-files"))

    @field_validator("para_root", "state_dir")
    @classmethod
    def _expand(cls, value: Path | None) -> Path | None:
        return None if value is None else value.expanduser()


class CoreSettings(PathSettings):
    """Effective settings for sort, explain, undo and clean."""

    para_root: Path  # required here, optional for ``init``
    preview_chars: int = Field(default=2000, ge=100, le=10_000)
    max_workers: int = Field(default=4, ge=1, le=16)
    fallback_enabled: bool = True
    fallback_model: str = "google/gemini-3.8-flash"
    fallback_backup_model: str = "anthropic/claude-sonnet-5.5"
    openrouter_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OPENROUTER_API_KEY", "PARA_FILES_OPENROUTER_API_KEY", "PARA_FILES_LLM_API_KEY"
        ),
    )
    calibration_min: int = Field(default=100, ge=1)
    fallback_green: float = Field(default=0.9, ge=0.0, le=1.0)
    fallback_red: float = Field(default=0.3, ge=0.0, le=1.0)
    cache_path: Path = Field(default_factory=lambda: _home(".cache", "para-files", "cache.sqlite"))

    @field_validator("cache_path")
    @classmethod
    def _expand_cache(cls, value: Path) -> Path:
        return value.expanduser()

    @field_validator("para_root")
    @classmethod
    def _check_root(cls, value: Path) -> Path:
        if BUCKET_NAME.match(value.name):
            msg = (
                f"para_root points at a bucket ({value.name}); set PARA_FILES_PARA_ROOT to the "
                f"folder that contains {INBOX}: {value}"
            )
            raise ValueError(msg)
        if not (value / INBOX).is_dir():
            msg = f"para_root has no {INBOX} folder: {value}"
            raise ValueError(msg)
        return value


def load_settings(**overrides: Any) -> CoreSettings:  # noqa: ANN401 - keyword overrides of any field
    """Settings from the environment, then ``<config dir>/.env``; overrides win over both."""
    return CoreSettings(_env_file=config_dir_path() / ".env", **overrides)  # type: ignore[call-arg]


def load_path_settings() -> PathSettings:
    """The root and state dir from the environment, then ``<config dir>/.env``."""
    return PathSettings(_env_file=config_dir_path() / ".env")  # type: ignore[call-arg]
