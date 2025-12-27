"""Tests for parallel processing functionality."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMLXEncoderThreadSafety:
    """Test thread-safety of MLX encoder lazy loading."""

    def test_encoder_load_lock_exists(self) -> None:
        """Test that MLXEncoder has a class-level lock."""
        from para_files.encoders.mlx_encoder import MLXEncoder

        assert hasattr(MLXEncoder, "_load_lock")
        assert isinstance(MLXEncoder._load_lock, type(threading.Lock()))

    @patch("para_files.encoders.mlx_encoder.EmbeddingModel")
    def test_encoder_concurrent_loading(self, mock_model: MagicMock) -> None:
        """Test that concurrent calls to _ensure_loaded only load once."""
        from para_files.encoders.mlx_encoder import MLXEncoder

        mock_model.from_registry.return_value = MagicMock()
        encoder = MLXEncoder()

        # Simulate concurrent loading
        load_count = 0
        original_from_registry = mock_model.from_registry

        def counting_from_registry(*args: object, **kwargs: object) -> MagicMock:
            nonlocal load_count
            load_count += 1
            return original_from_registry(*args, **kwargs)

        mock_model.from_registry = counting_from_registry

        # Run concurrent ensure_loaded calls
        def load_encoder() -> None:
            encoder._ensure_loaded()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(load_encoder) for _ in range(10)]
            for future in futures:
                future.result()

        # Model should only be loaded once due to locking
        assert load_count == 1
        assert encoder._loaded is True


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
