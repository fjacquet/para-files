"""Classification pipeline orchestrating 5-signal cascade.

Chains classifiers in priority order: first match wins.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from para_files.classifiers.book_detector import BookDetector
from para_files.classifiers.domain_kb import DomainKBClassifier
from para_files.classifiers.llm_fallback import LLMFallbackClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.classifiers.semantic_router import SemanticRouterClassifier
from para_files.classifiers.validated_db import ValidatedDBClassifier
from para_files.config import Config
from para_files.encoders.mlx_encoder import MLXEncoder
from para_files.reference_tree import ReferenceTree
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
)


if TYPE_CHECKING:
    from para_files.classifiers.base import BaseClassifier

logger = logging.getLogger(__name__)


class ClassificationPipeline:
    """Orchestrates 6-signal classification cascade.

    Classifiers are tried in priority order (highest confidence first):
    1. Validated DB (100%) - Manual mappings
    2. Rules Engine (95%) - Glob patterns
    2.5. Book Detector (92%, 100% with ISBN) - Technical books detection
    3. Domain KB (90%) - Known issuers
    4. Semantic Router (85%) - MLX embeddings
    5. LLM Fallback (configurable) - Optional AI

    First match wins. If nothing matches, returns default 0_Inbox.
    """

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._classifiers: list[BaseClassifier] = []
        self._reference_tree: ReferenceTree | None = None
        self._encoder: MLXEncoder | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize classifiers on first use."""
        if self._initialized:
            return

        # Load reference tree
        self._reference_tree = ReferenceTree(self._config.reference_tree_path)
        self._reference_tree.load()

        # Initialize classifiers in priority order
        self._classifiers = []

        # Signal 1: Validated DB (100%)
        validated_db = ValidatedDBClassifier(self._config.validated_db_path)
        self._classifiers.append(validated_db)

        # Signal 2: Rules Engine (95%)
        routing_rules = self._reference_tree.get_routing_rules()
        if routing_rules:
            rules_engine = RulesEngineClassifier(routing_rules)
            self._classifiers.append(rules_engine)

        # Signal 2.5: Book Detector (92%, 100% with ISBN)
        # Known technologies for livres classification
        technologies = [
            "Ansible",
            "C++",
            "Cloud",
            "Containers",
            "DevOps",
            "Go",
            "Java",
            "JavaScript",
            "Kubernetes",
            "Linux",
            "Network",
            "Node.js",
            "Python",
            "React",
            "Rust",
            "Security",
            "Shell",
            "Terraform",
            "TypeScript",
        ]
        book_detector = BookDetector(
            technologies=technologies,
            enable_isbn_lookup=True,
            base_pattern="3_Resources/livres/{technology}",
        )
        self._classifiers.append(book_detector)

        # Signal 3: Domain KB (90%)
        known_issuers = self._reference_tree.get_known_issuers()
        if known_issuers:
            domain_kb = DomainKBClassifier(known_issuers)
            self._classifiers.append(domain_kb)

        # Signal 4: Semantic Router (85%)
        routes = self._reference_tree.get_all_routes()
        routes_with_utterances = [r for r in routes if r.utterances]
        if routes_with_utterances:
            self._encoder = MLXEncoder(
                name=self._config.mlx.model_name,
                score_threshold=self._config.mlx.score_threshold,
            )
            semantic_router = SemanticRouterClassifier(
                encoder=self._encoder,
                routes=routes_with_utterances,
                score_threshold=self._config.mlx.score_threshold,
            )
            self._classifiers.append(semantic_router)

        # Signal 5: LLM Fallback (configurable)
        if self._config.llm.enabled:
            llm_fallback = LLMFallbackClassifier(
                enabled=True,
                model=self._config.llm.model,
                confidence_threshold=self._config.llm.confidence_threshold,
                api_base=self._config.llm.api_base,
                available_routes=routes,
            )
            self._classifiers.append(llm_fallback)

        self._initialized = True
        logger.info(
            "Pipeline initialized with %d classifiers: %s",
            len(self._classifiers),
            [c.name for c in self._classifiers],
        )

    def classify(
        self,
        content: str,
        metadata: FileMetadata | None = None,
    ) -> ClassificationResult:
        """Classify content through the pipeline.

        Tries each classifier in priority order until one succeeds.
        Returns default 0_Inbox if no classifier matches.

        Args:
            content: Text content to classify.
            metadata: Optional file metadata.

        Returns:
            ClassificationResult with category and confidence.
        """
        self._ensure_initialized()

        # Try each classifier in order
        for classifier in self._classifiers:
            try:
                result = classifier.classify(content, metadata)
                if result is not None:
                    logger.debug(
                        "Classified by %s: %s (%.0f%%)",
                        classifier.name,
                        result.category,
                        result.confidence.value * 100,
                    )
                    return result
            except Exception:
                logger.exception("Classifier %s failed", classifier.name)
                continue

        # Default to 0_Inbox
        logger.debug("No classifier matched, defaulting to 0_Inbox")
        return ClassificationResult(
            category="0_Inbox",
            confidence=Confidence(
                value=0.0,
                source=ClassificationSource.DEFAULT,
            ),
        )

    def classify_file(self, file_path: Path) -> ClassificationResult:
        """Classify a file by path.

        Extracts metadata and content preview, then classifies.

        Args:
            file_path: Path to file to classify.

        Returns:
            ClassificationResult with category and confidence.
        """
        from para_files.utils.file_utils import extract_file_metadata, read_content_preview

        # Extract metadata
        metadata = extract_file_metadata(file_path)

        # Read content preview
        content = read_content_preview(
            file_path,
            max_chars=self._config.content_preview_chars,
        )

        return self.classify(content, metadata)

    def get_target_path(self, result: ClassificationResult) -> Path:
        """Get full target path for a classification result.

        Args:
            result: Classification result with category.

        Returns:
            Full path under PARA root.
        """
        return self._config.para_root / result.category

    @property
    def classifiers(self) -> list[BaseClassifier]:
        """Return list of configured classifiers."""
        self._ensure_initialized()
        return self._classifiers.copy()
