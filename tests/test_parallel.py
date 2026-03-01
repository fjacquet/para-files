"""Tests for parallel processing functionality."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestOllamaEncoderThreadSafety:
    """Test thread-safety of Ollama encoder."""

    def test_encoder_has_fallback_chars(self) -> None:
        """Test that OllamaEncoder has fallback_chars attribute."""
        from para_files.encoders.ollama_encoder import OllamaEncoder

        encoder = OllamaEncoder()
        assert encoder.max_chars == 1000  # Default
        assert encoder.fallback_chars == 700  # Fallback for edge cases

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_encoder_fallback_on_error(self, mock_litellm: MagicMock) -> None:
        """Test that encoder uses fallback on batch failure."""
        from para_files.encoders.ollama_encoder import OllamaEncoder

        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "batch too large"
                raise RuntimeError(msg)
            mock_resp = MagicMock()
            mock_resp.data = [{"embedding": [0.1, 0.2, 0.3]}]
            return mock_resp

        mock_litellm.embedding.side_effect = side_effect

        encoder = OllamaEncoder()
        result = encoder(["test text " * 100])  # Long text

        assert result is not None
        assert len(result) == 1

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_encoder_concurrent_encoding(self, mock_litellm: MagicMock) -> None:
        """Test that concurrent encoding calls work correctly."""
        from para_files.encoders.ollama_encoder import OllamaEncoder

        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1] * 768}]
        mock_litellm.embedding.return_value = mock_resp

        encoder = OllamaEncoder()

        results = []

        def encode_text() -> None:
            result = encoder(["test text"])
            results.append(result)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(encode_text) for _ in range(10)]
            for future in futures:
                future.result()

        assert len(results) == 10


class TestGeolocationCacheThreadSafety:
    """Test thread-safety of geolocation cache."""

    def test_cache_has_lock(self) -> None:
        """Test that GeolocationCache has an RLock."""
        from para_files.utils.geolocation import GeolocationCache

        cache = GeolocationCache(db_path=Path("/tmp/test_geo_cache.db"))
        assert hasattr(cache, "_lock")
        assert isinstance(cache._lock, type(threading.RLock()))
        cache.close()

    def test_global_cache_lock_exists(self) -> None:
        """Test that global cache has a lock for initialization."""
        from para_files.utils import geolocation

        assert hasattr(geolocation, "_cache_lock")
        assert isinstance(geolocation._cache_lock, type(threading.Lock()))


class TestConfigMaxWorkers:
    """Test max_workers configuration option."""

    def test_config_has_max_workers(self) -> None:
        """Test that Config has max_workers field."""
        from para_files.config import Config

        config = Config()
        assert hasattr(config, "max_workers")
        assert config.max_workers == 1  # Default value

    def test_max_workers_bounds(self) -> None:
        """Test max_workers validation bounds."""
        from pydantic import ValidationError

        from para_files.config import Config

        # Valid values
        config = Config(max_workers=1)
        assert config.max_workers == 1

        config = Config(max_workers=16)
        assert config.max_workers == 16

        # Invalid: below minimum
        with pytest.raises(ValidationError):
            Config(max_workers=0)

        # Invalid: above maximum
        with pytest.raises(ValidationError):
            Config(max_workers=17)

    def test_max_workers_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test max_workers can be set from environment."""
        monkeypatch.setenv("PARA_FILES_MAX_WORKERS", "4")

        from para_files.config import Config

        config = Config()
        assert config.max_workers == 4


class TestParallelClassification:
    """Test parallel classification functionality."""

    @patch("para_files.main.ClassificationPipeline")
    def test_classify_uses_parallel_when_workers_gt_1(
        self,
        mock_pipeline_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that classify uses parallel processing when max_workers > 1."""
        from para_files.main import _classify_files_parallel

        # Create test files
        files = []
        for i in range(5):
            f = tmp_path / f"test_{i}.txt"
            f.write_text(f"content {i}")
            files.append(f)

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "test/category"
        mock_result.confidence.value = 0.95
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None
        mock_result.extracted_params = {}
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target/path")

        # Run parallel classification
        results = _classify_files_parallel(files, mock_pipeline, max_workers=3, output_json=True)

        # All files should be processed
        assert len(results) == 5
        # Pipeline should be called for each file
        assert mock_pipeline.classify_file.call_count == 5

    @patch("para_files.main.ClassificationPipeline")
    def test_classify_sequential_when_workers_eq_1(
        self,
        mock_pipeline_class: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that classify uses sequential processing when max_workers = 1."""
        from para_files.main import _classify_files_sequential

        # Create test files
        files = []
        for i in range(3):
            f = tmp_path / f"test_{i}.txt"
            f.write_text(f"content {i}")
            files.append(f)

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_result = MagicMock()
        mock_result.category = "test/category"
        mock_result.confidence.value = 0.95
        mock_result.confidence.source.value = "semantic"
        mock_result.route_name = None
        mock_result.extracted_params = {}
        mock_pipeline.classify_file.return_value = mock_result
        mock_pipeline.get_target_path.return_value = Path("/target/path")

        # Run sequential classification
        results = _classify_files_sequential(files, mock_pipeline, output_json=True)

        # All files should be processed
        assert len(results) == 3
