"""Signal 4: MLX-LM based classifier for Apple Silicon.

Replaces LLMFallbackClassifier (Ollama) with native MLX-LM inference.
No external server required - runs entirely in-process.

Requires: mlx-lm package (pip install mlx-lm)
Platform: macOS with Apple Silicon only
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


# System prompt for PARA classification
SYSTEM_PROMPT = """You are a file classification assistant for the PARA method.

PARA Categories:
- 0_Inbox: Temporary files to be sorted
- 1_Projects: Active projects with deadlines
- 2_Areas: Ongoing responsibilities (work, finances, health)
- 3_Resources: Reference materials (books, documentation, guides)
- 4_Archives: Completed/historical content (photos, invoices, old projects)

Sub-categories examples:
- 4_Archives/factures/{year}/{issuer} - Invoices by year and provider
- 4_Archives/banques/{bank}/{year} - Bank statements
- 4_Archives/assurances/{type}/{year} - Insurance documents
- 3_Resources/documentation/{technology} - Technical docs
- 3_Resources/livres/{topic} - Books by subject

Given the file content, respond ONLY with a JSON object:
{"category": "full/path", "confidence": 0.0-1.0, "reasoning": "brief explanation"}

Be specific with paths when possible. Extract year from dates if present."""


class MLXLLMClassifier(BaseClassifier):
    """Signal 4: MLX-LM fallback for unclassified files.

    Uses mlx-lm for native Apple Silicon inference without external servers.
    Model is loaded lazily on first classification request.

    Recommended models (all via mlx-community):
    - mlx-community/Qwen2.5-1.5B-Instruct-4bit (~1GB, fast)
    - mlx-community/Phi-3.5-mini-instruct-4bit (~2GB, balanced)
    - mlx-community/Llama-3.2-3B-Instruct-4bit (~2GB, capable)
    """

    def __init__(
        self,
        *,
        enabled: bool = False,
        model: str = "mlx-community/Qwen2.5-1.5B-Instruct-4bit",
        confidence_threshold: float = 0.6,
        content_preview_chars: int = DEFAULT_CONTENT_PREVIEW_CHARS,
        max_tokens: int = 256,
    ) -> None:
        """Initialize MLX-LM classifier.

        Args:
            enabled: Whether MLX-LM fallback is enabled.
            model: HuggingFace model ID (mlx-community recommended).
            confidence_threshold: Minimum confidence to accept result.
            content_preview_chars: Max characters of content to send.
            max_tokens: Maximum tokens to generate.
        """
        self._enabled = enabled
        self._model_name = model
        self._confidence_threshold = confidence_threshold
        self._content_preview_chars = content_preview_chars
        self._max_tokens = max_tokens

        # Lazy-loaded model and tokenizer
        self._model: Any | None = None
        self._tokenizer: Any | None = None

    @property
    def name(self) -> str:
        """Return classifier name."""
        return "mlx_llm"

    @property
    def source(self) -> ClassificationSource:
        """Return classification source."""
        return ClassificationSource.LLM_FALLBACK

    @property
    def default_confidence(self) -> float:
        """Return default confidence threshold."""
        return self._confidence_threshold

    def _load_model(self) -> bool:
        """Lazily load MLX-LM model.

        Returns:
            True if model loaded successfully, False otherwise.
        """
        if self._model is not None:
            return True

        try:
            from mlx_lm import load

            logger.info("Loading MLX-LM model: %s", self._model_name)
            # mlx_lm.load returns (model, tokenizer) tuple
            result = load(self._model_name)
            self._model = result[0]
            self._tokenizer = result[1]
            logger.info("MLX-LM model loaded successfully")
        except ImportError:
            logger.warning("mlx-lm not installed, MLX-LLM classifier disabled")
            return False
        except Exception:  # noqa: BLE001
            logger.exception("Failed to load MLX-LM model: %s", self._model_name)
            return False
        else:
            return True

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult | None:
        """Classify content using MLX-LM.

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

        # Load model lazily
        if not self._load_model():
            return None

        try:
            return self._generate_classification(content, metadata)
        except Exception:  # noqa: BLE001
            logger.exception("MLX-LLM classification failed")
            return None

    def _generate_classification(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> ClassificationResult | None:
        """Generate classification using MLX-LM.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult if successful, None otherwise.
        """
        from mlx_lm import generate

        if self._model is None or self._tokenizer is None:
            return None

        # Build prompt
        prompt = self._build_prompt(content, metadata)

        # Generate response
        response: str = generate(
            self._model,
            self._tokenizer,
            prompt=prompt,
            max_tokens=self._max_tokens,
            temp=0.0,  # Deterministic
        )

        return self._parse_response(response)

    def _build_prompt(
        self,
        content: str,
        metadata: FileMetadata | None,
    ) -> str:
        """Build prompt for MLX-LM.

        Uses chat template format for instruction-tuned models.

        Args:
            content: Text content.
            metadata: File metadata.

        Returns:
            Formatted prompt string.
        """
        # Build user message
        user_parts: list[str] = []

        if metadata:
            user_parts.append(f"Filename: {metadata.filename}")
            user_parts.append(f"Extension: {metadata.extension}")
            if metadata.modified_at:
                user_parts.append(f"Modified: {metadata.modified_at.strftime('%Y-%m-%d')}")

        # Truncate content
        preview = content[: self._content_preview_chars]
        user_parts.append(f"\nContent:\n{preview}")

        user_message = "\n".join(user_parts)

        # Use chat template if tokenizer supports it
        if self._tokenizer is not None and hasattr(self._tokenizer, "apply_chat_template"):
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
            result = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
            return str(result)

        # Fallback to simple format
        return f"{SYSTEM_PROMPT}\n\nUser: {user_message}\n\nAssistant:"

    def _parse_response(self, response: str) -> ClassificationResult | None:
        """Parse MLX-LM response.

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
                # Find JSON between code blocks
                match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                # Use match group or remove markers as fallback
                text = match.group(1) if match else re.sub(r"```(?:json)?", "", text).strip()

            # Find JSON object in response
            json_match = re.search(r"\{[^}]+\}", text, re.DOTALL)
            if not json_match:
                logger.debug("No JSON found in response: %s", text[:200])
                return None

            data = json.loads(json_match.group())

            category = data.get("category", "")
            confidence = float(data.get("confidence", 0.0))
            reasoning = data.get("reasoning", "")

            if not category:
                return None

            if confidence < self._confidence_threshold:
                logger.debug(
                    "MLX-LLM confidence %.2f below threshold %.2f",
                    confidence,
                    self._confidence_threshold,
                )
                return None

            return ClassificationResult(
                category=category,
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
            logger.debug("Failed to parse MLX-LLM response: %s - %s", e, response[:200])
            return None
