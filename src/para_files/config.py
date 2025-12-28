"""Configuration management for para-files.

Supports configuration from (in priority order):
1. Environment variables with PARA_FILES_ prefix
2. .env files in current directory
3. config section in reference tree YAML (personal_file_tree.yaml)
4. Default values

Example config section in YAML:
    config:
      para_root: "~/Documents/PARA"
      mlx:
        model_name: "nomic-text-v1.5"
        score_threshold: 0.8
      llm:
        enabled: false
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default reference tree location
DEFAULT_REFERENCE_TREE = Path("config/personal_file_tree.yaml")

# Default configuration values (centralized to avoid duplication)
DEFAULT_MLX_MODEL = "nomic-text-v1.5"
DEFAULT_SCORE_THRESHOLD = 0.75
DEFAULT_LLM_MODEL = "ollama/qwen2.5:1.5b"
DEFAULT_LLM_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_CONTENT_PREVIEW_CHARS = 2000


def _load_yaml_config(yaml_path: Path | None = None) -> dict[str, Any]:
    """Load config section from reference tree YAML.

    Args:
        yaml_path: Path to YAML file. If None, tries default locations.

    Returns:
        Config dict from YAML, or empty dict if not found.
    """
    paths_to_try = []
    if yaml_path:
        paths_to_try.append(yaml_path)
    paths_to_try.extend(
        [
            DEFAULT_REFERENCE_TREE,
            Path.cwd() / "config" / "personal_file_tree.yaml",
            Path.cwd() / "personal_file_tree.yaml",  # Backwards compatibility
        ]
    )

    for path in paths_to_try:
        if path.exists():
            with path.open() as f:
                data = yaml.safe_load(f) or {}
                config_section: dict[str, Any] = data.get("config", {})
                return config_section

    return {}


class MLXConfig(BaseSettings):
    """MLX embedding and LLM configuration (unified in v2.0).

    In v2.0, MLX handles both embeddings and optional LLM fallback.
    """

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_MLX_",
        extra="ignore",  # Allow extra fields for backward compatibility
        populate_by_name=True,  # Accept both field name and alias
    )

    # Embedding model configuration
    model_name: str = Field(
        default=DEFAULT_MLX_MODEL,
        alias="embedding_model",
        description="MLX embedding model from mlx-embedding-models registry",
    )
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic matching",
    )

    # LLM fallback configuration (v2.0 - optional native MLX-LM)
    llm_enabled: bool = Field(
        default=False,
        description="Enable native MLX-LM fallback for unclassified files",
    )
    llm_model: str = Field(
        default="mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        description="MLX-LM model for LLM fallback",
    )
    llm_confidence: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for LLM results",
    )


class LLMConfig(BaseSettings):
    """LLM fallback configuration using litellm."""

    model_config = SettingsConfigDict(env_prefix="PARA_FILES_LLM_")

    enabled: bool = Field(
        default=False,
        description="Enable LLM fallback for ambiguous classifications",
    )
    model: str = Field(
        default=DEFAULT_LLM_MODEL,
        description="LLM model identifier for litellm",
    )
    confidence_threshold: float = Field(
        default=DEFAULT_LLM_CONFIDENCE_THRESHOLD,
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
        default=Path.home() / "Documents" / "PARA",
        description="Root directory for PARA folders (0_Inbox, 1_Projects, etc.)",
    )

    # Reference tree configuration
    reference_tree_path: Path = Field(
        default=DEFAULT_REFERENCE_TREE,
        description="Path to the PARA reference tree YAML file",
    )

    # Validated DB for manual mappings
    validated_db_path: Path | None = Field(
        default=None,
        description="Path to JSON file with validated sender→category mappings",
    )

    # Content extraction settings
    content_preview_chars: int = Field(
        default=DEFAULT_CONTENT_PREVIEW_CHARS,
        ge=100,
        le=10000,
        description="Number of characters to extract for semantic matching",
    )

    # Parallel processing settings
    max_workers: int = Field(
        default=1,
        ge=1,
        le=16,
        description="Number of parallel workers for file processing (1=sequential)",
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


def load_config(
    reference_tree_path: Path | None = None,
    **overrides: object,
) -> Config:
    """Load configuration from YAML, environment, and optional overrides.

    Priority (highest to lowest):
    1. Explicit overrides passed to this function
    2. Environment variables (PARA_FILES_*)
    3. .env file
    4. config section in reference tree YAML
    5. Default values

    Args:
        reference_tree_path: Path to reference tree YAML with config section.
        **overrides: Configuration values to override all other settings.

    Returns:
        Loaded and validated Config instance.

    Raises:
        ValidationError: If required fields are missing or invalid.
    """
    # Load base config from YAML
    yaml_config = _load_yaml_config(reference_tree_path)

    # Handle nested configs from YAML
    mlx_yaml = yaml_config.pop("mlx", {})
    llm_yaml = yaml_config.pop("llm", {})

    # Expand ~ in para_root if present
    if "para_root" in yaml_config:
        yaml_config["para_root"] = Path(yaml_config["para_root"]).expanduser()

    # Build nested config objects (env vars override YAML)
    mlx_config = MLXConfig(**mlx_yaml)
    llm_config = LLMConfig(**llm_yaml)

    # Merge: YAML < env vars < overrides
    # pydantic-settings handles env var overlay automatically
    merged = {**yaml_config, "mlx": mlx_config, "llm": llm_config, **overrides}

    return Config(**merged)
