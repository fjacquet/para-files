"""Ollama-based encoder for semantic routing via litellm.

Uses litellm.embedding() to call Ollama's nomic-embed-text model
for 768-dimensional embeddings. Cross-platform replacement for MLX.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
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

    # In-memory LRU cache for embeddings (keyed by hash of first 2000 chars)
    _CACHE_MAX_SIZE: ClassVar[int] = 500
    _CACHE_CONTENT_CHARS: ClassVar[int] = 2000

    # Private attributes
    _initialized: bool = PrivateAttr(default=False)
    _cache: OrderedDict[str, list[float]] = PrivateAttr(default_factory=OrderedDict)

    def _cache_key(self, text: str) -> str:
        """Compute cache key from first 2000 chars of text."""
        content = text[: self._CACHE_CONTENT_CHARS]
        return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

    def _cache_get(self, key: str) -> list[float] | None:
        """Get embedding from cache, moving to end (LRU)."""
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def _cache_put(self, key: str, embedding: list[float]) -> None:
        """Store embedding in cache, evicting oldest if full."""
        self._cache[key] = embedding
        self._cache.move_to_end(key)
        while len(self._cache) > self._CACHE_MAX_SIZE:
            self._cache.popitem(last=False)

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
            except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) as e:
                logger.debug("Encode failed for {}-char text, trying shorter: {}", len(candidate), e)  # noqa: E501
                continue

        # Absolute last resort: encode just the first 100 chars
        last_chance = text[:100] if text else "document"
        try:
            result = self._encode_texts([last_chance])
            return result[0]
        except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) as e:
            logger.exception("Ollama encoder failed on 100-char text — server may be down: {}", e)
            return [0.0] * 768

    def __call__(self, texts: list[str]) -> list[list[float]]:
        """Encode texts to embeddings, using in-memory LRU cache to avoid redundant calls.

        Args:
            texts: List of texts to encode.

        Returns:
            List of embedding vectors as Python lists.
        """
        if not texts:
            return []

        results: list[list[float]] = []
        texts_to_encode: list[str] = []
        text_indices: list[int] = []

        # Check cache for each text
        for i, text in enumerate(texts):
            key = self._cache_key(text)
            cached = self._cache_get(key)
            if cached is not None:
                results.append(cached)
            else:
                results.append([])  # placeholder — filled in below
                texts_to_encode.append(self._truncate(text))
                text_indices.append(i)

        if not texts_to_encode:
            return results

        # Encode uncached texts
        try:
            new_embeddings = self._encode_texts(texts_to_encode)
        except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) as e:
            # Batch failed — retry per-text with progressive truncation
            logger.warning("Batch encode failed, retrying per-text: {}", e)
            new_embeddings = [self._encode_single(texts[i]) for i in text_indices]

        # Fill in results and update cache
        for idx, embedding in zip(text_indices, new_embeddings, strict=True):
            results[idx] = embedding
            key = self._cache_key(texts[idx])
            self._cache_put(key, embedding)

        return results

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
