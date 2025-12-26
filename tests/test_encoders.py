"""Tests for the encoders module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from para_files.encoders.base import BaseEncoder
from para_files.encoders.mlx_encoder import MLXEncoder


class ConcreteEncoder(BaseEncoder):
    """Concrete implementation for testing abstract base."""

    @property
    def name(self) -> str:
        return "test_encoder"

    def __call__(self, texts: list[str]) -> list[list[float]]:
        # Return dummy embeddings of dimension 384
        return [[0.1] * 384 for _ in texts]


class TestBaseEncoder:
    """Tests for the abstract BaseEncoder class."""

    def test_cannot_instantiate_abstract(self):
        """Test that BaseEncoder cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEncoder()  # type: ignore[abstract]

    def test_concrete_encoder_implements_interface(self):
        """Test that concrete encoder implements the interface."""
        encoder = ConcreteEncoder()
        assert encoder.name == "test_encoder"
        result = encoder(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == 384


class TestMLXEncoder:
    """Tests for MLXEncoder class."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        encoder = MLXEncoder()
        assert encoder.name == "nomic-text-v1.5"
        assert encoder.score_threshold == 0.75
        assert encoder._loaded is False

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        encoder = MLXEncoder(
            name="bge-small",
            score_threshold=0.8,
        )
        assert encoder.name == "bge-small"
        assert encoder.score_threshold == 0.8

    def test_lazy_loading(self):
        """Test that model is not loaded on init."""
        encoder = MLXEncoder()
        assert encoder._model is None
        assert encoder._loaded is False

    def test_empty_input(self):
        """Test encoding empty list returns empty list."""
        encoder = MLXEncoder()
        # Don't need to load model for empty input
        result = encoder([])
        assert result == []

    @patch("para_files.encoders.mlx_encoder.EmbeddingModel.from_registry")
    def test_ensure_loaded(self, mock_from_registry: MagicMock):
        """Test model loading on first use."""
        mock_model = MagicMock()
        mock_from_registry.return_value = mock_model

        encoder = MLXEncoder()
        encoder._ensure_loaded()

        assert encoder._loaded is True
        mock_from_registry.assert_called_once_with("nomic-text-v1.5")

    @patch("para_files.encoders.mlx_encoder.EmbeddingModel.from_registry")
    def test_only_loads_once(self, mock_from_registry: MagicMock):
        """Test model is only loaded once."""
        mock_model = MagicMock()
        mock_from_registry.return_value = mock_model

        encoder = MLXEncoder()
        encoder._ensure_loaded()
        encoder._ensure_loaded()
        encoder._ensure_loaded()

        mock_from_registry.assert_called_once()


class TestMLXEncoderIntegration:
    """Integration tests for MLXEncoder (require model download).

    These tests are marked slow and require an actual MLX model.
    Skip with: pytest -m "not slow"
    """

    @pytest.mark.slow
    def test_encode_single_text(self):
        """Test encoding a single text."""
        encoder = MLXEncoder()
        result = encoder(["This is a test document about insurance."])
        assert len(result) == 1
        assert len(result[0]) > 0  # Should have embedding dimensions
        assert all(isinstance(x, float) for x in result[0])

    @pytest.mark.slow
    def test_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        encoder = MLXEncoder()
        texts = [
            "Invoice from insurance company",
            "Bank statement for January",
            "Electricity bill",
        ]
        result = encoder(texts)
        assert len(result) == 3
        assert all(len(emb) == len(result[0]) for emb in result)

    @pytest.mark.slow
    def test_embeddings_are_normalized(self):
        """Test that embeddings are L2 normalized."""
        import math

        encoder = MLXEncoder()
        result = encoder(["Test document"])
        embedding = result[0]

        # Check L2 norm is approximately 1
        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.01

    @pytest.mark.slow
    def test_encode_batch(self):
        """Test batch encoding."""
        encoder = MLXEncoder()
        texts = [f"Document {i}" for i in range(10)]
        result = encoder.encode_batch(texts, batch_size=3)
        assert len(result) == 10

    @pytest.mark.slow
    def test_similar_texts_have_similar_embeddings(self):
        """Test that semantically similar texts have similar embeddings."""
        encoder = MLXEncoder()
        result = encoder(
            [
                "Invoice for health insurance premium",
                "Insurance invoice for premium payment",
                "Bank account statement for checking",
            ]
        )

        # Compute cosine similarity between embeddings
        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b)

        # Similar texts should have higher similarity
        sim_12 = cosine_sim(result[0], result[1])  # Both about insurance
        sim_13 = cosine_sim(result[0], result[2])  # Insurance vs bank

        # Insurance texts should be more similar to each other
        assert sim_12 > sim_13
