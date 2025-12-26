"""Signal 5: LLM fallback classifier (configurable confidence).

Uses litellm to call LLM APIs (Ollama, Gemini, OpenRouter) for
classifying content that couldn't be matched by other signals.
"""

from __future__ import annotations

import json
import logging

from para_files.classifiers.base import BaseClassifier
from para_files.config import DEFAULT_CONTENT_PREVIEW_CHARS
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    Route,
)


logger = logging.getLogger(__name__)


# System prompt for classification
SYSTEM_PROMPT = (
    "You are a file classification assistant. "
    "Your task is to classify files into the PARA method categories.\n\n"
    "PARA Categories:\n"
    "- 0_Inbox: Temporary files to be sorted\n"
    "- 1_Projects: Active projects with deadlines\n"
    "- 2_Areas: Ongoing responsibilities (work, finances, health)\n"
    "- 3_Resources: Reference materials (books, documentation, guides)\n"
    "- 4_Archives: Completed/historical content (photos, invoices, old projects)\n\n"
    "Given the file content or metadata, respond with a JSON object:\n"
    "{\n"
    '    "category": "full/path/to/category",\n'
    '    "confidence": 0.0-1.0,\n'
    '    "reasoning": "brief explanation"\n'
    "}\n\n"
    "Be specific with the category path when possible "
    '(e.g., "4_Archives/factures/2025/_Cloud/Netflix" instead of just "4_Archives").'
)


class LLMFallbackClassifier(BaseClassifier):
    """Signal 5: LLM fallback for ambiguous cases (configurable confidence).

    Uses litellm to access various LLM providers:
    - Ollama (local): "ollama/qwen2.5:1.5b"
    - Gemini: "gemini/gemini-pro"
    - OpenRouter: "openrouter/..."

    This classifier is optional and only used when enabled and
    previous classifiers couldn't determine a category.
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        model: str = "ollama/qwen2.5:1.5b",
        confidence_threshold: float = 0.6,
        api_base: str | None = None,
        available_routes: list[Route] | None = None,
        content_preview_chars: int = DEFAULT_CONTENT_PREVIEW_CHARS,
    ) -> None:
        """Initialize LLM fallback classifier.

        Args:
            enabled: Whether LLM fallback is enabled.
            model: LLM model identifier for litellm.
            confidence_threshold: Minimum confidence to accept LLM result.
            api_base: Optional API base URL for Ollama.
            available_routes: List of available routes for context.
            content_preview_chars: Max characters of content to send to LLM.
        """
        self._enabled = enabled
        self._model = model
        self._confidence_threshold = confidence_threshold
        self._api_base = api_base
        self._available_routes = available_routes or []
        self._content_preview_chars = content_preview_chars

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "llm_fallback"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.LLM_FALLBACK

    @property
    def default_confidence(self) -> float:
        """Return default confidence (from LLM response)."""
        return self._confidence_threshold

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using LLM.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if LLM provides confident classification, None otherwise.
        """
        if not self._enabled:
            return None

        if not content.strip():
            return None

        try:
            return self._call_llm(content, metadata)
        except Exception:
            logger.exception("LLM classification failed")
            return None

    def _call_llm(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult | None:
        """Call LLM API for classification.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if successful, None otherwise.
        """
        # Import litellm here to avoid import errors if not installed
        try:
            import litellm
        except ImportError:
            logger.warning("litellm not installed, LLM fallback disabled")
            return None

        # Build user message with content and metadata
        user_message = self._build_user_message(content, metadata)

        # Call LLM
        response = litellm.completion(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            api_base=self._api_base,
            temperature=0.0,  # Deterministic output
        )

        # Parse response
        response_text = response.choices[0].message.content
        if not response_text:
            return None

        return self._parse_llm_response(response_text)

    def _build_user_message(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> str:
        """Build user message for LLM.

        Args:
            content: Text content.
            metadata: File metadata.

        Returns:
            Formatted user message.
        """
        parts = []

        if metadata:
            parts.append(f"Filename: {metadata.filename}")
            parts.append(f"Extension: {metadata.extension}")
            if metadata.modified_at:
                parts.append(f"Modified: {metadata.modified_at.isoformat()}")

        parts.append(f"\nContent preview:\n{content[: self._content_preview_chars]}")

        if self._available_routes:
            route_names = [r.name for r in self._available_routes[:20]]
            parts.append(f"\nAvailable categories: {', '.join(route_names)}")

        return "\n".join(parts)

    def _parse_llm_response(self, response_text: str) -> ClassificationResult | None:
        """Parse LLM JSON response.

        Args:
            response_text: Raw LLM response.

        Returns:
            ClassificationResult if parsing succeeds, None otherwise.
        """
        try:
            # Try to extract JSON from response
            # Handle cases where LLM wraps JSON in markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code block
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            data = json.loads(text)

            category = data.get("category", "")
            confidence = float(data.get("confidence", 0.0))

            if not category or confidence < self._confidence_threshold:
                return None

            return ClassificationResult(
                category=category,
                confidence=Confidence(
                    value=confidence,
                    source=self.source,
                ),
                extracted_params={"llm_reasoning": data.get("reasoning", "")},
            )

        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Failed to parse LLM response: %s", response_text[:200])
            return None
