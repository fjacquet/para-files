"""Tests for the encoders module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from para_files.encoders.base import BaseEncoder
from para_files.encoders.ollama_encoder import OllamaEncoder


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


class TestOllamaEncoder:
    """Tests for OllamaEncoder class."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        encoder = OllamaEncoder()
        assert encoder.name == "nomic-embed-text"
        assert encoder.score_threshold == 0.75
        assert encoder.type == "ollama"

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        encoder = OllamaEncoder(
            name="bge-small",
            score_threshold=0.8,
        )
        assert encoder.name == "bge-small"
        assert encoder.score_threshold == 0.8

    def test_empty_input(self):
        """Test encoding empty list returns empty list."""
        encoder = OllamaEncoder()
        result = encoder([])
        assert result == []

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_encode_calls_litellm(self, mock_litellm: MagicMock):
        """Test that encoding calls litellm.embedding()."""
        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1] * 768}]
        mock_litellm.embedding.return_value = mock_response

        encoder = OllamaEncoder()
        result = encoder(["hello world"])

        mock_litellm.embedding.assert_called_once()
        assert len(result) == 1
        assert len(result[0]) == 768

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_encode_multiple_texts(self, mock_litellm: MagicMock):
        """Test encoding multiple texts."""
        mock_response = MagicMock()
        mock_response.data = [
            {"embedding": [0.1] * 768},
            {"embedding": [0.2] * 768},
            {"embedding": [0.3] * 768},
        ]
        mock_litellm.embedding.return_value = mock_response

        encoder = OllamaEncoder()
        result = encoder(["text1", "text2", "text3"])

        assert len(result) == 3

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_truncation(self, mock_litellm: MagicMock):
        """Test that long texts are truncated."""
        mock_response = MagicMock()
        mock_response.data = [{"embedding": [0.1] * 768}]
        mock_litellm.embedding.return_value = mock_response

        encoder = OllamaEncoder(max_chars=100)
        encoder(["x" * 500])

        # Verify the text was truncated
        call_args = mock_litellm.embedding.call_args
        texts_sent = call_args.kwargs.get("input") or call_args[1].get("input")
        assert len(texts_sent[0]) == 100


class TestOllamaEncoderFallback:
    """Tests for per-text retry logic on batch failure."""

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_batch_failure_retries_per_text(self, mock_litellm: MagicMock):
        """Batch failure triggers per-text retry with progressive truncation."""
        call_count = 0

        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "batch too large"
                raise RuntimeError(msg)
            mock_resp = MagicMock()
            mock_resp.data = [{"embedding": [0.5] * 768}]
            return mock_resp

        mock_litellm.embedding.side_effect = side_effect

        encoder = OllamaEncoder()
        result = encoder(["x" * 2000])

        assert len(result) == 1
        assert result[0] != [0.0] * 768

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_encode_batch(self, mock_litellm: MagicMock):
        """Test batch encoding."""
        mock_response = MagicMock()
        mock_response.data = [
            {"embedding": [0.1] * 768},
            {"embedding": [0.2] * 768},
            {"embedding": [0.3] * 768},
        ]
        mock_litellm.embedding.return_value = mock_response

        encoder = OllamaEncoder()
        result = encoder.encode_batch(
            [f"Document {i}" for i in range(9)],
            batch_size=3,
        )
        assert len(result) == 9

    @patch("para_files.encoders.ollama_encoder.litellm")
    def test_total_failure_returns_zero_vector(self, mock_litellm: MagicMock):
        """When all retries fail, returns zero vector."""
        mock_litellm.embedding.side_effect = RuntimeError("server down")

        encoder = OllamaEncoder()
        result = encoder(["test"])

        assert len(result) == 1
        assert result[0] == [0.0] * 768


class TestBackwardCompatibility:
    """Test backward compatibility aliases."""

    def test_mlx_encoder_alias(self):
        """Test that MLXEncoder is an alias for OllamaEncoder."""
        from para_files.encoders import MLXEncoder

        assert MLXEncoder is OllamaEncoder


class TestOllamaEncoderIntegration:
    """Integration tests for OllamaEncoder (require running Ollama server).

    These tests are marked slow and require Ollama with nomic-embed-text.
    Skip with: pytest -m "not slow"
    """

    @pytest.mark.slow
    def test_encode_single_text(self):
        """Test encoding a single text."""
        encoder = OllamaEncoder()
        result = encoder(["This is a test document about insurance."])
        assert len(result) == 1
        assert len(result[0]) > 0
        assert all(isinstance(x, float) for x in result[0])

    @pytest.mark.slow
    def test_encode_multiple_texts(self):
        """Test encoding multiple texts."""
        encoder = OllamaEncoder()
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

        encoder = OllamaEncoder()
        result = encoder(["Test document"])
        embedding = result[0]

        norm = math.sqrt(sum(x * x for x in embedding))
        assert abs(norm - 1.0) < 0.1  # Ollama embeddings may not be perfectly normalized

    @pytest.mark.slow
    def test_encode_batch(self):
        """Test batch encoding."""
        encoder = OllamaEncoder()
        texts = [f"Document {i}" for i in range(10)]
        result = encoder.encode_batch(texts, batch_size=3)
        assert len(result) == 10

    @pytest.mark.slow
    def test_similar_texts_have_similar_embeddings(self):
        """Test that semantically similar texts have similar embeddings."""
        encoder = OllamaEncoder()
        result = encoder(
            [
                "Invoice for health insurance premium",
                "Insurance invoice for premium payment",
                "Bank account statement for checking",
            ]
        )

        def cosine_sim(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            norm_a = sum(x * x for x in a) ** 0.5
            norm_b = sum(x * x for x in b) ** 0.5
            return dot / (norm_a * norm_b)

        sim_12 = cosine_sim(result[0], result[1])
        sim_13 = cosine_sim(result[0], result[2])

        assert sim_12 > sim_13
