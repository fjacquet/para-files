"""Tests for the config module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from para_files.config import (
    DEFAULT_LLM_CONFIDENCE_THRESHOLD,
    DEFAULT_LLM_MODEL,
    DEFAULT_MLX_MODEL,
    DEFAULT_REFERENCE_TREE,
    DEFAULT_SCORE_THRESHOLD,
    Config,
    LLMConfig,
    MLXConfig,
    _load_yaml_config,
    load_config,
)


class TestMLXConfig:
    """Tests for MLXConfig."""

    def test_default_values(self):
        """Test default MLX configuration values."""
        config = MLXConfig()
        assert config.model_name == DEFAULT_MLX_MODEL
        assert config.score_threshold == DEFAULT_SCORE_THRESHOLD

    def test_custom_values(self):
        """Test custom MLX configuration values."""
        config = MLXConfig(model_name="custom/model", score_threshold=0.8)
        assert config.model_name == "custom/model"
        assert config.score_threshold == 0.8

    def test_threshold_boundaries(self):
        """Test score threshold at boundaries."""
        low = MLXConfig(score_threshold=0.0)
        high = MLXConfig(score_threshold=1.0)
        assert low.score_threshold == 0.0
        assert high.score_threshold == 1.0

    def test_threshold_out_of_range(self):
        """Test that out-of-range threshold fails."""
        with pytest.raises(ValidationError):
            MLXConfig(score_threshold=1.5)
        with pytest.raises(ValidationError):
            MLXConfig(score_threshold=-0.1)


class TestLLMConfig:
    """Tests for LLMConfig."""

    def test_default_values(self):
        """Test default LLM configuration values."""
        config = LLMConfig()
        assert config.enabled is False
        assert config.model == DEFAULT_LLM_MODEL
        assert config.confidence_threshold == DEFAULT_LLM_CONFIDENCE_THRESHOLD
        assert config.api_base is None

    def test_enabled_config(self):
        """Test LLM configuration when enabled."""
        config = LLMConfig(
            enabled=True,
            model="openai/gpt-4",
            confidence_threshold=0.8,
            api_base="https://api.openai.com/v1",
        )
        assert config.enabled is True
        assert config.model == "openai/gpt-4"
        assert config.api_base == "https://api.openai.com/v1"


class TestConfig:
    """Tests for Config."""

    def test_minimal_config(self, tmp_path: Path):
        """Test config with only required field."""
        config = Config(para_root=tmp_path)
        assert config.para_root == tmp_path
        assert config.reference_tree_path == Path("config/personal_file_tree.yaml")
        assert config.validated_db_path is None

    def test_full_config(self, tmp_path: Path):
        """Test config with all fields."""
        ref_tree = tmp_path / "tree.yaml"
        validated_db = tmp_path / "validated.json"

        config = Config(
            para_root=tmp_path,
            reference_tree_path=ref_tree,
            validated_db_path=validated_db,
            content_preview_chars=5000,
            mlx=MLXConfig(score_threshold=0.8),
            llm=LLMConfig(enabled=True),
        )
        assert config.reference_tree_path == ref_tree
        assert config.validated_db_path == validated_db
        assert config.content_preview_chars == 5000
        assert config.mlx.score_threshold == 0.8
        assert config.llm.enabled is True

    def test_para_paths(self, tmp_path: Path):
        """Test PARA folder path properties."""
        config = Config(para_root=tmp_path)
        assert config.inbox_path == tmp_path / "0_Inbox"
        assert config.projects_path == tmp_path / "1_Projects"
        assert config.areas_path == tmp_path / "2_Areas"
        assert config.resources_path == tmp_path / "3_Resources"
        assert config.archives_path == tmp_path / "4_Archives"

    def test_content_preview_chars_boundaries(self, tmp_path: Path):
        """Test content preview character limits."""
        low = Config(para_root=tmp_path, content_preview_chars=100)
        high = Config(para_root=tmp_path, content_preview_chars=10000)
        assert low.content_preview_chars == 100
        assert high.content_preview_chars == 10000

    def test_content_preview_chars_out_of_range(self, tmp_path: Path):
        """Test that out-of-range preview chars fails."""
        with pytest.raises(ValidationError):
            Config(para_root=tmp_path, content_preview_chars=50)
        with pytest.raises(ValidationError):
            Config(para_root=tmp_path, content_preview_chars=20000)

    def test_para_root_has_default(self):
        """Test that para_root has a sensible default."""
        from pathlib import Path

        config = Config()
        assert config.para_root == Path.home() / "Documents" / "PARA"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_with_overrides(self, tmp_path: Path):
        """Test loading config with overrides."""
        config = load_config(para_root=tmp_path)
        assert config.para_root == tmp_path

    def test_load_with_nested_overrides(self, tmp_path: Path):
        """Test loading config with nested overrides."""
        config = load_config(
            para_root=tmp_path,
            mlx=MLXConfig(score_threshold=0.9),
        )
        assert config.mlx.score_threshold == 0.9


class TestYAMLConfig:
    """Tests for YAML configuration loading from reference tree."""

    def test_default_reference_tree_path(self):
        """Test default reference tree path."""
        assert Path("config/personal_file_tree.yaml") == DEFAULT_REFERENCE_TREE

    def test_load_yaml_config_from_file(self, tmp_path: Path):
        """Test loading config from a YAML file."""
        yaml_file = tmp_path / "test_tree.yaml"
        yaml_file.write_text("""
config:
  para_root: "/custom/para"
  mlx:
    model_name: "custom-model"
    score_threshold: 0.85
  llm:
    enabled: true
""")
        config_dict = _load_yaml_config(yaml_file)
        assert config_dict["para_root"] == "/custom/para"
        assert config_dict["mlx"]["model_name"] == "custom-model"
        assert config_dict["mlx"]["score_threshold"] == 0.85
        assert config_dict["llm"]["enabled"] is True

    def test_load_yaml_config_missing_file(self, tmp_path: Path, monkeypatch):
        """Test loading config when YAML file doesn't exist."""
        fake_path = tmp_path / "nonexistent.yaml"
        # Change to tmp_path so cwd fallback also fails
        monkeypatch.chdir(tmp_path)
        with patch("para_files.config.DEFAULT_REFERENCE_TREE", fake_path):
            config_dict = _load_yaml_config(fake_path)
            assert config_dict == {}

    def test_load_yaml_config_no_config_section(self, tmp_path: Path):
        """Test loading config from YAML without config section."""
        yaml_file = tmp_path / "test_tree.yaml"
        yaml_file.write_text("""
routes:
  - name: "test-route"
    path: "/test"
""")
        config_dict = _load_yaml_config(yaml_file)
        assert config_dict == {}

    def test_load_config_from_yaml(self, tmp_path: Path):
        """Test full config loading from YAML."""
        yaml_file = tmp_path / "test_tree.yaml"
        yaml_file.write_text("""
config:
  para_root: "~/TestPARA"
  mlx:
    score_threshold: 0.9
""")
        config = load_config(reference_tree_path=yaml_file)
        assert config.para_root == Path.home() / "TestPARA"
        assert config.mlx.score_threshold == 0.9

    def test_config_defaults_without_yaml(self, tmp_path: Path):
        """Test that config loads with defaults when no YAML exists."""
        fake_path = tmp_path / "nonexistent.yaml"
        with patch("para_files.config.DEFAULT_REFERENCE_TREE", fake_path):
            config = load_config(reference_tree_path=fake_path)
            # Should still work with defaults
            assert config.mlx.model_name == DEFAULT_MLX_MODEL
            assert config.mlx.score_threshold == DEFAULT_SCORE_THRESHOLD
