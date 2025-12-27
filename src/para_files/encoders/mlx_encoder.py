"""MLX-based encoder for semantic routing.

Uses mlx-embedding-models to load embedding models optimized for Apple Silicon.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, ClassVar

from mlx_embedding_models.embedding import EmbeddingModel  # type: ignore[import-untyped]
from pydantic import ConfigDict, PrivateAttr
from semantic_router.encoders import DenseEncoder


logger = logging.getLogger(__name__)


class MLXEncoder(DenseEncoder):
    """Custom encoder for semantic-router using MLX embeddings.

    This encoder inherits from DenseEncoder (Pydantic model) and uses
    mlx-embedding-models for optimized inference on Apple Silicon.

    Available models in registry:
        - nomic-text-v1.5 (default, 768 dims, 8192 token context)
        - nomic-text-v1 (768 dims)
        - bge-small (384 dims)
        - bge-base (768 dims)
        - bge-large (1024 dims)
        - minilm-l6 (384 dims)
        - minilm-l12 (384 dims)
        - multilingual-e5-small (384 dims)
    """

    name: str = "nomic-text-v1.5"
    score_threshold: float | None = 0.75
    type: str = "mlx"
    # Max chars to avoid exceeding model's token limit
    # mlx-embedding-models uses buckets up to 512 tokens max
    # ~2 chars per token average, with 700 fallback for edge cases
    max_chars: int = 1000
    fallback_chars: int = 700

    model_config: ClassVar[ConfigDict] = ConfigDict(arbitrary_types_allowed=True)

    # Class-level lock for thread-safe model loading
    _load_lock: ClassVar[threading.Lock] = threading.Lock()

    # Private attributes for lazy loading
    _model: Any = PrivateAttr(default=None)
    _loaded: bool = PrivateAttr(default=False)

    def _ensure_loaded(self) -> None:
        """Lazily load model on first use (thread-safe with double-check pattern)."""
        if not self._loaded:
            with self._load_lock:
                if not self._loaded:  # Double-check after acquiring lock
                    self._model = EmbeddingModel.from_registry(self.name)
                    self._loaded = True

    def _truncate(self, text: str) -> str:
        """Truncate text to max_chars to avoid exceeding model's token limit."""
        if len(text) > self.max_chars:
            return text[: self.max_chars]
        return text

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings.

        Args:
            texts: List of texts to encode.

        Returns:
            List of embedding vectors as Python lists.
        """
        if not texts:
            return []

        self._ensure_loaded()

        # Truncate texts to avoid exceeding model's token limit
        truncated_texts = [self._truncate(t) for t in texts]

        try:
            # EmbeddingModel.encode returns numpy array of shape (n_texts, embedding_dim)
            embeddings_array = self._model.encode(truncated_texts)
        except IndexError as e:
            # Token length exceeds model's maximum sequence length
            # This can happen with texts that tokenize poorly (lots of numbers, symbols)
            logger.warning("Text exceeds token limit, using fallback truncation: %s", e)
            # Retry with fallback_chars (700) for safety
            shorter_texts = [t[: self.fallback_chars] for t in texts]
            try:
                embeddings_array = self._model.encode(shorter_texts)
            except IndexError:
                # Still too long, return empty embeddings
                logger.exception("Text still exceeds token limit after truncation")
                # Return zero vectors of expected dimension (768 for nomic)
                return [[0.0] * 768 for _ in texts]

        # Convert to list of lists
        embeddings: list[list[float]] = embeddings_array.tolist()
        return embeddings

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
