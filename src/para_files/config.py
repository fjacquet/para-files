"""Configuration management for para-files.

Supports environment variables with PARA_FILES_ prefix and .env files.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLXConfig(BaseSettings):
    """MLX embedding model configuration."""

    model_config = SettingsConfigDict(env_prefix="PARA_FILES_MLX_")

    model_name: str = Field(
        default="mlx-community/nomic-embed-text-v1.5",
        description="MLX embedding model from Hugging Face",
    )
    score_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic matching",
    )


class LLMConfig(BaseSettings):
    """LLM fallback configuration using litellm."""

    model_config = SettingsConfigDict(env_prefix="PARA_FILES_LLM_")

    enabled: bool = Field(
        default=False,
        description="Enable LLM fallback for ambiguous classifications",
    )
    model: str = Field(
        default="ollama/qwen2.5:1.5b",
        description="LLM model identifier for litellm",
    )
    confidence_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence from LLM to accept classification",
    )
    api_base: str | None = Field(
        default=None,
        description="API base URL for Ollama or other providers",
    )


class Config(BaseSettings):
    """Root configuration for para-files classification system."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PARA filesystem root
    para_root: Path = Field(
        description="Root directory for PARA folders (0_Inbox, 1_Projects, etc.)",
    )

    # Reference tree configuration
    reference_tree_path: Path = Field(
        default=Path("personal_file_tree.yaml"),
        description="Path to the PARA reference tree YAML file",
    )

    # Validated DB for manual mappings
    validated_db_path: Path | None = Field(
        default=None,
        description="Path to JSON file with validated sender→category mappings",
    )

    # Content extraction settings
    content_preview_chars: int = Field(
        default=2000,
        ge=100,
        le=10000,
        description="Number of characters to extract for semantic matching",
    )

    # Nested configurations
    mlx: MLXConfig = Field(default_factory=MLXConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @property
    def inbox_path(self) -> Path:
        """Return the full path to 0_Inbox."""
        return self.para_root / "0_Inbox"

    @property
    def projects_path(self) -> Path:
        """Return the full path to 1_Projects."""
        return self.para_root / "1_Projects"

    @property
    def areas_path(self) -> Path:
        """Return the full path to 2_Areas."""
        return self.para_root / "2_Areas"

    @property
    def resources_path(self) -> Path:
        """Return the full path to 3_Resources."""
        return self.para_root / "3_Resources"

    @property
    def archives_path(self) -> Path:
        """Return the full path to 4_Archives."""
        return self.para_root / "4_Archives"


def load_config(**overrides: object) -> Config:
    """Load configuration from environment and optional overrides.

    Args:
        **overrides: Configuration values to override environment settings.

    Returns:
        Loaded and validated Config instance.

    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    return Config(**overrides)  # type: ignore[arg-type]
