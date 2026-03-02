"""Signal 6: LLM-based classifier via litellm/Ollama.

Uses litellm to call Ollama (or any compatible provider) for fallback
classification when all other signals fail.

Requires: litellm package + running Ollama server (or other provider)
"""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger

from para_files.classifiers.base import BaseClassifier
from para_files.config import DEFAULT_CONTENT_PREVIEW_CHARS
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


# Valid PARA top-level prefixes for output validation
_VALID_PARA_PREFIXES = ("0_Inbox", "1_Projects", "2_Areas", "3_Resources", "4_Archives")


def _build_system_prompt(valid_categories: list[str]) -> str:
    """Build a system prompt that constrains LLM output to valid PARA categories.

    Groups categories by domain to help the LLM reason about classification.

    Args:
        valid_categories: List of valid PARA category paths from the taxonomy.

    Returns:
        System prompt string with real categories.
    """
    if valid_categories:
        # Group categories by domain for better LLM reasoning
        tech_cats = [c for c in valid_categories if "documentation" in c or "docs/" in c]
        resource_cats = [
            c for c in valid_categories if c.startswith("3_Resources") and c not in tech_cats
        ]
        archive_cats = [c for c in valid_categories if c.startswith("4_Archives")]
        other_cats = [
            c
            for c in valid_categories
            if c not in tech_cats and c not in resource_cats and c not in archive_cats
        ]

        sections: list[str] = []
        if tech_cats:
            sections.append("TECHNICAL DOCUMENTATION:\n" + "\n".join(f"- {c}" for c in tech_cats))
        if resource_cats:
            sections.append("RESOURCES:\n" + "\n".join(f"- {c}" for c in resource_cats))
        if archive_cats:
            sections.append("ARCHIVES:\n" + "\n".join(f"- {c}" for c in archive_cats))
        if other_cats:
            sections.append("OTHER:\n" + "\n".join(f"- {c}" for c in other_cats))

        category_list = "\n\n".join(sections)
    else:
        category_list = (
            "- 3_Resources/documentation/{technology}\n- 4_Archives/5y_divers/{year}\n- 0_Inbox"
        )

    return f"""You are a file classification assistant for the PARA method.

STEP 1 - Determine the domain:
- English technical document (IT, software, hardware): use 3_Resources/documentation/{{technology}}
- If the document is a French administrative document: pick from ARCHIVES categories below
- If unsure: use 0_Inbox

STEP 2 - Pick the exact category from this list:

{category_list}

Rules:
- Replace {{technology}} with the actual technology name (e.g., Dell, Cisco, VMware)
- Replace {{issuer}} with the company/organization name
- Replace {{year}} with the 4-digit year extracted from the content
- Use 0_Inbox ONLY if absolutely no category fits
- NEVER invent paths outside this list
- NEVER output absolute file paths (no / or C:\\ at the start)

Respond ONLY with a JSON object:
{{"category": "exact/path/from/list", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""


class LLMClassifier(BaseClassifier):
    """Signal 6: LLM fallback for unclassified files.

    Uses litellm to call Ollama or any compatible LLM provider.
    No model loading required - delegates to external server.

    Default model: ollama/ministral-3:8b (8B params, good classification)
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        model: str = "ollama/ministral-3:8b",
        confidence_threshold: float = 0.6,
        content_preview_chars: int = DEFAULT_CONTENT_PREVIEW_CHARS,
        max_tokens: int = 256,
        api_base: str | None = None,
        valid_categories: list[str] | None = None,
    ) -> None:
        """Initialize LLM classifier.

        Args:
            enabled: Whether LLM fallback is enabled.
            model: litellm model identifier (e.g., ollama/ministral-3:8b).
            confidence_threshold: Minimum confidence to accept result.
            content_preview_chars: Max characters of content to send.
            max_tokens: Maximum tokens to generate.
            api_base: API base URL for Ollama or other providers.
            valid_categories: List of valid PARA category paths from the taxonomy.
        """
        self._enabled = enabled
        self._model_name = model
        self._confidence_threshold = confidence_threshold
        self._content_preview_chars = content_preview_chars
        self._max_tokens = max_tokens
        self._api_base = api_base
        self._system_prompt = _build_system_prompt(valid_categories or [])

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "llm"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.LLM_FALLBACK

    @property
    def default_confidence(self) -> float:
        """Return default confidence threshold."""
        return self._confidence_threshold

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using LLM via litellm.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if confident classification, None otherwise.
        """
        if not self._enabled:
            return None

        if not content.strip():
            return None

        try:
            return self._generate_classification(content, metadata)
        except Exception:  # noqa: BLE001
            logger.exception("LLM classification failed")
            return None

    def _generate_classification(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult | None:
        """Generate classification using litellm.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if successful, None otherwise.
        """
        import litellm

        # Build user message
        user_message = self._build_user_message(content, metadata)

        # Build optional kwargs for api_base
        kwargs: dict[str, Any] = {}
        if self._api_base:
            kwargs["api_base"] = self._api_base

        response = litellm.completion(
            model=self._model_name,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=self._max_tokens,
            **kwargs,
        )

        text = response.choices[0].message.content or ""
        logger.debug("LLM raw response: {}", text[:500])

        return self._parse_response(text)

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
            Formatted user message string.
        """
        parts: list[str] = []

        if metadata:
            parts.append(f"Filename: {metadata.filename}")
            parts.append(f"Extension: {metadata.extension}")
            if metadata.modified_at:
                parts.append(f"Modified: {metadata.modified_at.strftime('%Y-%m-%d')}")

        # Truncate content
        preview = content[: self._content_preview_chars]
        parts.append(f"\nContent:\n{preview}")

        return "\n".join(parts)

    def _sanitize_category(self, category: str) -> str | None:
        """Validate and sanitize a category path from the LLM.

        Rejects hallucinated absolute paths, Windows paths, and categories
        that don't start with a valid PARA top-level folder.

        Args:
            category: Raw category string from LLM output.

        Returns:
            Sanitized category string, or None if invalid.
        """
        category = category.strip().strip('"').strip("'")

        # Reject absolute or Windows-style paths
        if category.startswith(("/", "~")) or ":\\" in category or category[1:2] == ":":
            logger.debug("LLM rejected hallucinated path: {}", category[:100])
            return None

        # Must start with a valid PARA prefix
        if not any(category.startswith(p) for p in _VALID_PARA_PREFIXES):
            logger.debug("LLM rejected non-PARA category: {}", category[:100])
            return None

        return category

    def _parse_response(self, response: str) -> ClassificationResult | None:
        """Parse LLM response.

        Args:
            response: Raw model response.

        Returns:
            ClassificationResult if parsing succeeds, None otherwise.
        """
        try:
            # Extract JSON from response (handle markdown code blocks)
            text = response.strip()

            # Remove markdown code blocks if present
            if "```" in text:
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                text = match.group(1) if match else re.sub(r"```(?:json)?", "", text).strip()

            # Find JSON object with "category" key (handles nested braces better)
            json_match = re.search(r'\{[^{}]*"category"[^{}]*\}', text, re.DOTALL)
            if not json_match:
                logger.debug("No JSON found in LLM response: {}", text[:200])
                return None

            data = json.loads(json_match.group())

            category = data.get("category", "")
            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")

            if not category:
                return None

            # Validate category is a valid PARA path (reject hallucinated paths)
            sanitized = self._sanitize_category(category)
            if not sanitized:
                return None

            if confidence < self._confidence_threshold:
                logger.debug(
                    "LLM confidence {:.2f} below threshold {:.2f}",
                    confidence,
                    self._confidence_threshold,
                )
                return None

            return ClassificationResult(
                category=sanitized,
                confidence=Confidence(
                    value=confidence,
                    source=self.source,
                ),
                extracted_params={
                    "llm_reasoning": reasoning,
                    "llm_model": self._model_name,
                },
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug("Failed to parse LLM response: {} - {}", e, response[:200])
            return None
