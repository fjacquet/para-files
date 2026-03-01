"""Ollama-based encoder for semantic routing via litellm.

Uses litellm.embedding() to call Ollama's nomic-embed-text model
for 768-dimensional embeddings. Cross-platform replacement for MLX.
"""

from __future__ import annotations

from typing import ClassVar

import litellm
from loguru import logger
from pydantic import ConfigDict, PrivateAttr
from semantic_router.encoders import DenseEncoder


class OllamaEncoder(DenseEncoder):
    """Custom encoder for semantic-router using Ollama embeddings via litellm.

    This encoder inherits from DenseEncoder (Pydantic model) and uses
    litellm.embedding() to call Ollama's embedding endpoint.

    Default model: nomic-embed-text (768 dims, same as MLX variant).
    """

    name: str = "nomic-embed-text"
    score_threshold: float | None = 0.75
    type: str = "ollama"
    api_base: str = "http://localhost:11434"

    # Max chars to avoid excessive token usage
    max_chars: int = 1000
    fallback_chars: int = 700

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    # Private attribute tracking initialization
    _initialized: bool = PrivateAttr(default=False)

    def _truncate(self, text: str) -> str:
        """Truncate text to max_chars to avoid excessive token usage."""
        if len(text) > self.max_chars:
            return text[: self.max_chars]
        return text

    def _encode_texts(self, texts: list[str]) -> list[list[float]]:
        """Encode texts via litellm.embedding().

        Args:
            texts: List of texts to encode.

        Returns:
            List of embedding vectors as Python lists.
        """
        response = litellm.embedding(
            model=f"ollama/{self.name}",
            input=texts,
            api_base=self.api_base,
        )
        return [item["embedding"] for item in response.data]

    def _encode_single(self, text: str) -> list[float]:
        """Encode a single text with progressive truncation on failure.

        Tries progressively shorter truncations (fallback_chars, 400, 200)
        before giving up and returning a zero vector.

        Args:
            text: Text to encode.

        Returns:
            Embedding vector as a list of floats.
        """
        candidates = [
            text[: self.fallback_chars],
            text[:400],
            text[:200],
        ]
        for candidate in candidates:
            try:
                result = self._encode_texts([candidate])
                return result[0]
            except Exception:  # noqa: BLE001
                logger.debug("Encode failed for {}-char text, trying shorter", len(candidate))
                continue

        # Absolute last resort: encode just the first 100 chars
        last_chance = text[:100] if text else "document"
        try:
            result = self._encode_texts([last_chance])
            return result[0]
        except Exception:  # noqa: BLE001
            logger.exception("Ollama encoder failed on 100-char text — server may be down")
            return [0.0] * 768

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode.

        Returns:
            List of embedding vectors as Python lists.
        """
        if not texts:
            return []

        # Truncate texts
        truncated_texts = [self._truncate(t) for t in texts]

        try:
            return self._encode_texts(truncated_texts)
        except Exception as e:  # noqa: BLE001
            # Batch failed — retry per-text with progressive truncation
            logger.warning("Batch encode failed, retrying per-text: {}", e)
            return [self._encode_single(t) for t in texts]

    def encode_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Encode texts in batches for efficiency.

        Args:
            texts: List of texts to encode.
            batch_size: Number of texts per batch.

        Returns:
            List of embedding vectors.
        """
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings


# Backward compatibility alias
MLXEncoder = OllamaEncoder
