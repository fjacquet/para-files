"""Semantic classifier using MLX embeddings.

This classifier uses sentence embeddings to semantically match document content
against category descriptions from the taxonomy. It serves as a fallback when
pattern-based matching fails.
"""

from __future__ import annotations

import math
import re

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.encoders.mlx_encoder import MLXEncoder
from para_files.taxonomies.loader import TaxonomyLoader, get_taxonomy_loader
from para_files.taxonomies.models import DocumentCategory, DocumentType
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


# Minimum content length for semantic matching
MIN_CONTENT_LENGTH = 50

# Maximum content length to encode
MAX_CONTENT_LENGTH = 2000


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def _extract_year(content: str, metadata: FileMetadata | None) -> str | None:
    """Extract year from content or metadata.

    Args:
        content: Document content.
        metadata: Optional file metadata.

    Returns:
        Year string if found, None otherwise.
    """
    # Check filename first
    if metadata and metadata.filename:
        year_match = re.search(r"(20\d{2}|19\d{2})", metadata.filename)
        if year_match:
            return year_match.group(1)

    # Fallback to content
    year_match = re.search(r"(20\d{2}|19\d{2})", content[:500])
    if year_match:
        return year_match.group(1)

    return None


def _resolve_pattern(para_pattern: str, extracted_params: dict[str, str]) -> str:
    """Resolve a para_pattern by replacing placeholders.

    Args:
        para_pattern: Pattern with {placeholders}.
        extracted_params: Dict of extracted values.

    Returns:
        Resolved path string.
    """
    category_path = para_pattern
    for key, value in extracted_params.items():
        category_path = category_path.replace(f"{{{key}}}", value)

    # Remove remaining placeholders
    category_path = re.sub(r"\{[^}]+\}", "", category_path)
    # Clean up double slashes
    return re.sub(r"/+", "/", category_path).rstrip("/")


class SemanticClassifier(BaseClassifier):
    """Semantic classifier using MLX embeddings.

    This classifier pre-computes embeddings for all document type descriptions
    from the taxonomy, then matches incoming documents against these embeddings
    using cosine similarity.

    Attributes:
        confidence_threshold: Minimum similarity score to return a match.
        default_confidence: Base confidence value for semantic matches (85%).
    """

    def __init__(
        self,
        loader: TaxonomyLoader | None = None,
        confidence_threshold: float = 0.5,
        *,
        enabled: bool = True,
    ) -> None:
        """Initialize the semantic classifier.

        Args:
            loader: TaxonomyLoader instance (uses global if not provided).
            confidence_threshold: Minimum cosine similarity to accept a match.
            enabled: Whether the classifier is enabled.
        """
        self._loader = loader or get_taxonomy_loader()
        self._confidence_threshold = confidence_threshold
        self._enabled = enabled

        # Lazy-loaded components
        self._encoder: MLXEncoder | None = None
        self._category_embeddings: dict[str, list[float]] = {}
        self._category_info: dict[str, dict[str, str]] = {}  # category -> metadata
        self._initialized = False

    @property
    def name(self) -> str:
        """Return classifier name for logging."""
        return "SemanticClassifier"

    @property
    def source(self) -> ClassificationSource:
        """Return the classification source."""
        return ClassificationSource.SEMANTIC_ROUTER

    @property
    def default_confidence(self) -> float:
        """Return default confidence for semantic matches (85%)."""
        return 0.85

    def _build_category_text(
        self,
        doc_type: DocumentType,
        category: DocumentCategory,
    ) -> str:
        """Build a text description for embedding from document type metadata.

        Combines name, description, keywords, and related terms to create
        a rich semantic representation.
        """
        parts = [f"Catégorie: {category.name}"]

        # Document type name (e.g., "Déclarations d'impôts")
        if doc_type.name:
            parts.append(f"Type: {doc_type.name}")

        # Description if available (from category)
        if category.description:
            parts.append(category.description)

        # Keywords
        if doc_type.keywords:
            parts.append(f"Mots-clés: {', '.join(doc_type.keywords)}")

        # Required context terms
        if doc_type.required_context:
            parts.append(f"Contexte: {', '.join(doc_type.required_context)}")

        return " | ".join(parts)

    def _ensure_initialized(self) -> None:
        """Lazily initialize encoder and compute category embeddings."""
        if self._initialized:
            return

        logger.info("Initializing SemanticClassifier with MLX embeddings...")

        # Initialize encoder
        self._encoder = MLXEncoder()

        # Build category descriptions from taxonomy
        texts_to_embed: list[str] = []
        category_keys: list[str] = []

        taxonomy = self._loader.load_documents()

        for category in taxonomy.categories:
            for doc_type in category.documents:
                self._process_doc_type(
                    doc_type,
                    category,
                    texts_to_embed,
                    category_keys,
                )

        if not texts_to_embed:
            logger.warning("No categories found for semantic classification")
            self._initialized = True
            return

        # Compute embeddings for all categories
        logger.info("Computing embeddings for {} document types...", len(texts_to_embed))
        embeddings = self._encoder.encode_batch(texts_to_embed, batch_size=32)

        # Store embeddings
        for key, embedding in zip(category_keys, embeddings, strict=True):
            self._category_embeddings[key] = embedding

        logger.info(
            "SemanticClassifier initialized with {} category embeddings",
            len(self._category_embeddings),
        )
        self._initialized = True

    def _process_doc_type(
        self,
        doc_type: DocumentType,
        category: DocumentCategory,
        texts_to_embed: list[str],
        category_keys: list[str],
    ) -> None:
        """Process a single document type for embedding.

        Args:
            doc_type: Document type from taxonomy.
            category: Parent category.
            texts_to_embed: List to append text to.
            category_keys: List to append keys to.
        """
        # Determine the para_pattern (doc-level overrides category-level)
        doc_para_pattern = doc_type.para_pattern or category.para_pattern

        if not doc_para_pattern:
            return

        # Build unique key
        category_key = f"{category.name}/{doc_type.sub_id}"

        # Build text for embedding
        text = self._build_category_text(doc_type, category)
        texts_to_embed.append(text)
        category_keys.append(category_key)

        # Store category info for later retrieval
        self._category_info[category_key] = {
            "category_name": category.name,
            "sub_id": doc_type.sub_id,
            "para_pattern": doc_para_pattern,
            "retention": doc_type.retention,
            "name": doc_type.name,
        }

    def _find_best_match(
        self,
        content_embedding: list[float],
    ) -> tuple[str | None, float]:
        """Find the best matching category for a content embedding.

        Args:
            content_embedding: Embedding vector for the content.

        Returns:
            Tuple of (best_key, best_similarity).
        """
        best_key: str | None = None
        best_similarity: float = 0.0

        for key, cat_embedding in self._category_embeddings.items():
            similarity = _cosine_similarity(content_embedding, cat_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_key = key

        return best_key, best_similarity

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using semantic similarity.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if a match is found above threshold, None otherwise.
        """
        if not self._enabled or not content or len(content.strip()) < MIN_CONTENT_LENGTH:
            return None

        self._ensure_initialized()

        if not self._encoder or not self._category_embeddings:
            return None

        # Encode the document content
        try:
            content_embedding = self._encoder([content[:MAX_CONTENT_LENGTH]])[0]
        except (IndexError, ValueError, RuntimeError) as e:
            logger.debug("Failed to encode content: {}", e)
            return None

        # Find best matching category
        best_key, best_similarity = self._find_best_match(content_embedding)

        if best_key is None or best_similarity < self._confidence_threshold:
            logger.debug(
                "No semantic match found (best: %.2f, threshold: %.2f)",
                best_similarity,
                self._confidence_threshold,
            )
            return None

        return self._build_result(best_key, best_similarity, content, metadata)

    def _build_result(
        self,
        best_key: str,
        best_similarity: float,
        content: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult | None:
        """Build the classification result from a match.

        Args:
            best_key: Key of the matched category.
            best_similarity: Similarity score.
            content: Original content.
            metadata: File metadata.

        Returns:
            ClassificationResult or None if pattern is invalid.
        """
        # Get category info
        info = self._category_info.get(best_key, {})
        para_pattern = info.get("para_pattern", "")

        if not para_pattern:
            return None

        # Extract year if needed
        extracted_params: dict[str, str] = {}
        if "{year}" in para_pattern:
            year = _extract_year(content, metadata)
            if year:
                extracted_params["year"] = year

        # Calculate final category path
        category_path = _resolve_pattern(para_pattern, extracted_params)

        # Adjust confidence based on similarity
        adjusted_confidence = self.default_confidence * best_similarity

        logger.info(
            "Semantic match: %s -> %s (similarity: %.2f, confidence: %.2f)",
            info.get("name", best_key),
            category_path,
            best_similarity,
            adjusted_confidence,
        )

        return ClassificationResult(
            category=category_path,
            confidence=Confidence(
                value=adjusted_confidence,
                source=self.source,
            ),
            route_name=info.get("name"),
            extracted_params=extracted_params,
            raw_score=best_similarity,
        )
