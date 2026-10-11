"""Settings of the new core (spec §4.1, settings precedence).

Sources, highest first: init arguments, environment variables, ``<config dir>/.env``,
defaults. There is no YAML source and no working-directory ``.env``, so the result does not
depend on where a command runs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from para_files.config import config_dir_path


INBOX = "0_Inbox"
BUCKET_NAME = re.compile(r"^[0-4]_")


def _home(*parts: str) -> Path:
    return Path.home().joinpath(*parts)


_MODEL_CONFIG = SettingsConfigDict(
    env_prefix="PARA_FILES_",
    env_file_encoding="utf-8",
    extra="ignore",
    populate_by_name=True,
)


def _state_dir_field() -> Any:  # noqa: ANN401 - a pydantic Field, shared by two settings classes
    return Field(default_factory=lambda: _home(".local", "state", "para-files"))


class PathSettings(BaseSettings):
    """The two paths ``init`` needs before the PARA root has an inbox: no root check."""

    model_config = _MODEL_CONFIG

    para_root: Path | None = None
    state_dir: Path = _state_dir_field()

    @field_validator("para_root", "state_dir")
    @classmethod
    def _expand(cls, value: Path | None) -> Path | None:
        return None if value is None else value.expanduser()


class CoreSettings(BaseSettings):
    """Effective settings for sort, explain, undo and clean."""

    model_config = _MODEL_CONFIG

    para_root: Path
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
    issuers_green: float = Field(default=0.9, ge=0.0, le=1.0)
    fallback_green: float = Field(default=0.9, ge=0.0, le=1.0)
    fallback_red: float = Field(default=0.3, ge=0.0, le=1.0)
    cache_path: Path = Field(default_factory=lambda: _home(".cache", "para-files", "cache.sqlite"))
    state_dir: Path = _state_dir_field()

    @field_validator("para_root", "cache_path", "state_dir")
    @classmethod
    def _expand(cls, value: Path) -> Path:
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
