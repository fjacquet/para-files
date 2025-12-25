"""MLX-based encoder for semantic routing.

Uses mlx-lm to load embedding models from Hugging Face
and encode texts for semantic similarity matching.
"""

from __future__ import annotations

from typing import Any

import mlx.core as mx
from mlx_lm import load


class MLXEncoder:
    """Custom encoder for semantic-router using MLX embeddings.

    This encoder implements the interface expected by semantic-router
    while using MLX for optimized inference on Apple Silicon.
    """

    def __init__(
        self,
        model_name: str = "mlx-community/nomic-embed-text-v1.5",
        score_threshold: float = 0.75,
    ) -> None:
        """Initialize MLX encoder with model.

        Args:
            model_name: Hugging Face model identifier.
            score_threshold: Minimum similarity score for matching.
        """
        self._model_name = model_name
        self._score_threshold = score_threshold
        self._model: Any = None
        self._tokenizer: Any = None
        self._loaded = False

    @property
    def name(self) -> str:
        """Return encoder name."""
        return self._model_name

    @property
    def score_threshold(self) -> float:
        """Return minimum similarity score threshold."""
        return self._score_threshold

    def _ensure_loaded(self) -> None:
        """Lazily load model on first use."""
        if not self._loaded:
            # load() returns (model, tokenizer, tokenizer_config)
            result = load(self._model_name)
            self._model = result[0]
            self._tokenizer = result[1]
            self._loaded = True

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

        embeddings: list[list[float]] = []

        for text in texts:
            # Tokenize
            inputs = self._tokenizer(
                text,
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=512,
            )

            # Convert to MLX arrays
            input_ids = mx.array(inputs["input_ids"])
            attention_mask = mx.array(inputs["attention_mask"])

            # Get embeddings from model
            outputs = self._model(input_ids)

            # Mean pooling over sequence length
            # outputs shape: (batch_size, seq_len, hidden_size)
            masked_outputs = outputs * attention_mask[:, :, None]
            sum_embeddings = mx.sum(masked_outputs, axis=1)
            sum_mask = mx.sum(attention_mask, axis=1, keepdims=True)
            mean_embeddings = sum_embeddings / mx.maximum(sum_mask, mx.array(1e-9))

            # L2 normalize
            norm = mx.sqrt(mx.sum(mean_embeddings * mean_embeddings, axis=-1, keepdims=True))
            normalized = mean_embeddings / mx.maximum(norm, mx.array(1e-9))

            # Convert to Python list
            embedding_list: list[float] = normalized[0].tolist()  # type: ignore[assignment]
            embeddings.append(embedding_list)

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
