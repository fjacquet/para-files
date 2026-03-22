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
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Default reference tree location
DEFAULT_REFERENCE_TREE = Path("config/personal_file_tree.yaml")

# Default configuration values (centralized to avoid duplication)
DEFAULT_MLX_MODEL = "nomic-text-v1.5"
DEFAULT_SCORE_THRESHOLD = 0.75
DEFAULT_LLM_MODEL = "ollama/ministral-3:8b"
DEFAULT_LLM_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_CONTENT_PREVIEW_CHARS = 2000

# Logging defaults
DEFAULT_LOG_ROTATION = "10 MB"
DEFAULT_LOG_RETENTION = "30 days"
DEFAULT_LOG_LEVEL = "INFO"


# Global config file location — searched before local .env so local .env takes precedence.
# Users who run para-files outside the project directory should place their settings here.
_HOME_ENV = Path.home() / ".config" / "para-files" / ".env"
_ENV_FILES = (str(_HOME_ENV), ".env")


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
    """Embedding configuration (formerly MLX, now Ollama via litellm).

    Env prefix kept as PARA_FILES_MLX_ for backward compatibility.
    LLM settings have moved to LLMConfig (PARA_FILES_LLM_*).
    """

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_MLX_",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",  # Allow extra fields for backward compatibility
        populate_by_name=True,  # Accept both field name and alias
    )

    # Embedding model configuration
    model_name: str = Field(
        default=DEFAULT_MLX_MODEL,
        alias="embedding_model",
        description="Embedding model name (used by Ollama via litellm)",
    )
    score_threshold: float = Field(
        default=DEFAULT_SCORE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score for semantic matching",
    )

    # Semantic classifier configuration
    semantic_enabled: bool = Field(
        default=True,
        description="Enable semantic classifier using Ollama embeddings",
    )
    semantic_threshold: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity threshold for semantic matching",
    )


class LLMConfig(BaseSettings):
    """LLM fallback configuration using litellm/Ollama."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_LLM_",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    enabled: bool = Field(
        default=True,
        description="Enable LLM fallback via litellm/Ollama",
    )
    model: str = Field(
        default=DEFAULT_LLM_MODEL,
        description="LLM model identifier for litellm (e.g., ollama/ministral-3:8b)",
    )
    confidence_threshold: float = Field(
        default=DEFAULT_LLM_CONFIDENCE_THRESHOLD,
        ge=0.0,
        le=1.0,
        description="Minimum confidence from LLM to accept classification",
    )
    api_base: str | None = Field(
        default="http://localhost:11434",
        description="API base URL for Ollama or other providers",
    )
    timeout: float = Field(
        default=15.0,
        gt=0.0,
        description="Request timeout in seconds for LLM calls",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for cloud LLM providers (e.g., OpenRouter). Passed to litellm.",
    )


class LoggingConfig(BaseSettings):
    """Logging configuration for file and console output."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_LOG_",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    level: str = Field(
        default=DEFAULT_LOG_LEVEL,
        description="Log level for file output (DEBUG, INFO, WARNING, ERROR)",
    )
    rotation: str = Field(
        default=DEFAULT_LOG_ROTATION,
        description="Log file rotation size (e.g., '10 MB', '100 MB', '1 GB')",
    )
    retention: str = Field(
        default=DEFAULT_LOG_RETENTION,
        description="Log file retention period (e.g., '7 days', '30 days', '1 year')",
    )
    compression: str = Field(
        default="gz",
        description="Compression format for rotated logs (gz, bz2, xz, zip)",
    )


class OCRRenameConfig(BaseModel):
    """Configuration for OCR-based file renaming."""

    enabled: bool = Field(
        default=True,
        description="Enable OCR-based renaming of generic filenames before classification",
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to perform rename",
    )
    dry_run: bool = Field(
        default=False,
        description="If True, log renames but don't actually rename files",
    )


class ExtensionRoutingConfig(BaseSettings):
    """Configuration for extension-based routing classifier.

    Provides destination folder paths for media, security, script, and other
    file types that are best classified by their extension alone.
    """

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_EXT_ROUTING_",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    media_video_folder: str = Field(
        default="3_Resources/media/video",
        description="Destination for video files (.3gp, .m4v, .mp4, .mov)",
    )
    media_audio_folder: str = Field(
        default="3_Resources/media/audio",
        description="Destination for audio files (.m4a, .mp3)",
    )
    media_images_folder: str = Field(
        default="3_Resources/media/images",
        description="Destination for raster image files (.gif, .tif, .tiff, .psd)",
    )
    security_folder: str = Field(
        default="3_Resources/security",
        description="Destination for security files (.p7b, .asc, .kdbx)",
    )
    scripts_folder: str = Field(
        default="3_Resources/dev/scripts",
        description="Destination for script and web files (.ps1, .css, .js, .sh)",
    )
    catchall_folder: str = Field(
        default="0_Inbox",
        description="Destination for files with unrecognised extensions",
    )


class Config(BaseSettings):
    """Root configuration for para-files classification system."""

    model_config = SettingsConfigDict(
        env_prefix="PARA_FILES_",
        env_nested_delimiter="__",
        env_file=_ENV_FILES,
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
        default=4,
        ge=1,
        le=16,
        description="Number of parallel workers for file processing (1=sequential)",
    )

    # Nested configurations
    mlx: MLXConfig = Field(default_factory=MLXConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ocr_rename: OCRRenameConfig = Field(default_factory=OCRRenameConfig)
    extension_routing: ExtensionRoutingConfig = Field(default_factory=ExtensionRoutingConfig)

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
    logging_yaml = yaml_config.pop("logging", {})

    # Expand ~ in para_root if present
    if "para_root" in yaml_config:
        yaml_config["para_root"] = Path(yaml_config["para_root"]).expanduser()

    # Build nested config objects (env vars override YAML)
    mlx_config = MLXConfig(**mlx_yaml)
    llm_config = LLMConfig(**llm_yaml)
    logging_config = LoggingConfig(**logging_yaml)

    # Merge: YAML < env vars < overrides
    # pydantic-settings handles env var overlay automatically
    merged = {
        **yaml_config,
        "mlx": mlx_config,
        "llm": llm_config,
        "logging": logging_config,
        **overrides,
    }

    return Config(**merged)
