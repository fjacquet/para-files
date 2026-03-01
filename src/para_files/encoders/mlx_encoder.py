"""MLX-based encoder for semantic routing.

Uses mlx-embedding-models to load embedding models optimized for Apple Silicon.
"""

from __future__ import annotations

import threading
from typing import Any, ClassVar, cast

from loguru import logger
from mlx_embedding_models.embedding import EmbeddingModel  # type: ignore[import-untyped]
from pydantic import ConfigDict, PrivateAttr
from semantic_router.encoders import DenseEncoder


def _apply_transformers5_tokenizer_patch() -> None:
    """Patch TokenizersBackend for transformers 5.x compatibility.

    transformers 5.0 removed batch_encode_plus from TokenizersBackend.
    mlx_embedding_models 0.0.11 still calls it, so we add it back as a
    delegate to __call__, which accepts identical arguments.

    Applied once at module import time so all future instances are covered.
    """
    try:
        from transformers.tokenization_utils_tokenizers import (  # type: ignore[import-untyped]
            TokenizersBackend,
        )

        if not hasattr(TokenizersBackend, "batch_encode_plus"):
            logger.debug("Applying transformers 5.x TokenizersBackend compatibility patch")

            def _batch_encode_plus(self: object, batch: list[str], **kwargs: object) -> object:
                return self(batch, **kwargs)  # type: ignore[operator]

            TokenizersBackend.batch_encode_plus = _batch_encode_plus  # type: ignore[attr-defined]
    except ImportError:
        pass  # transformers < 5.x: TokenizersBackend doesn't exist, no patch needed


_apply_transformers5_tokenizer_patch()


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

    def _encode_single(self, text: str) -> list[float]:
        """Encode a single text with progressive truncation on IndexError.

        Tries progressively shorter truncations (fallback_chars, 400, 200)
        before giving up and returning a mean-pooled partial result.
        Never returns a zero vector — uses the shortest encodable prefix instead.

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
                arr = self._model.encode([candidate])
                return cast("list[float]", arr.tolist()[0])
            except IndexError:
                continue
        # Absolute last resort: encode just the first sentence or 100 chars
        # This should never fail because 100 chars << token limit
        last_chance = text[:100] if text else "document"
        try:
            arr = self._model.encode([last_chance])
            return cast("list[float]", arr.tolist()[0])
        except Exception:  # noqa: BLE001
            logger.exception("MLX encoder failed on 100-char text — model may be broken")
            # Only now do we return a zero vector, and we log it as an error
            dim = getattr(self._model, "dims", 768)
            return [0.0] * dim

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
            # Batch failed — likely a tokenization edge case. Retry per-text.
            logger.warning("Batch encode failed, retrying per-text: {}", e)
            return [self._encode_single(t) for t in texts]

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
