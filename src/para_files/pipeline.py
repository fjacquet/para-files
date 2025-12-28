"""Classification pipeline orchestrating 4-signal cascade.

Pipeline v2.0 - Simplified with taxonomy-based classification:
1. RulesEngine (95%) - Extension/pattern based routing
2. BookDetector (92%) - ISBN detection + Thema classification
3. TaxonomyClassifier (90%) - Issuers + keywords from documents.json
4. MLXLLMClassifier (60%) - Optional LLM fallback via mlx-lm

Chains classifiers in priority order: first match wins.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from para_files.classifiers.book_detector import BookDetector
from para_files.classifiers.mlx_llm_classifier import MLXLLMClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.classifiers.taxonomy_classifier import TaxonomyClassifier
from para_files.config import Config
from para_files.reference_tree import ReferenceTree
from para_files.taxonomies.loader import get_taxonomy_loader
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
    """Orchestrates 4-signal classification cascade (v2.0).

    Simplified pipeline using JSON taxonomies:
    1. Rules Engine (95%) - Extension/pattern based routing
    2. Book Detector (92%, 100% with ISBN) - ISBN + Thema classification
    3. Taxonomy Classifier (90%) - Issuers + keywords from documents.json
    4. MLX-LLM Fallback (60%) - Optional native Apple Silicon LLM

    First match wins. If nothing matches, returns default 0_Inbox.

    Key changes from v1.0:
    - Removed: ValidatedDB, DomainKB, SemanticRouter
    - Added: TaxonomyClassifier (unified issuer + keyword matching)
    - Replaced: LLMFallback (Ollama) with MLXLLMClassifier (native MLX)
    """

    def __init__(self, config: Config) -> None:
        """Initialize pipeline with configuration.

        Args:
            config: Application configuration.
        """
        self._config = config
        self._classifiers: list[BaseClassifier] = []
        self._reference_tree: ReferenceTree | None = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily initialize classifiers on first use."""
        if self._initialized:
            return

        # Load reference tree (for routing_rules only in v2.0)
        self._reference_tree = ReferenceTree(self._config.reference_tree_path)
        self._reference_tree.load()

        # Load taxonomy for TaxonomyClassifier
        taxonomy_loader = get_taxonomy_loader()

        # Initialize classifiers in priority order
        self._classifiers = []

        # Signal 1: Rules Engine (95%) - Extension/pattern based routing
        routing_rules = self._reference_tree.get_routing_rules()
        if routing_rules:
            rules_engine = RulesEngineClassifier(routing_rules)
            self._classifiers.append(rules_engine)

        # Signal 2: Book Detector (92%, 100% with ISBN)
        # Technologies from routing_rules or defaults
        technologies = self._get_known_technologies()
        book_detector = BookDetector(
            technologies=technologies,
            enable_isbn_lookup=True,
            base_pattern="3_Resources/livres/{technology}",
        )
        self._classifiers.append(book_detector)

        # Signal 3: Taxonomy Classifier (90%) - Issuers + keywords from documents.json
        taxonomy_classifier = TaxonomyClassifier(loader=taxonomy_loader)
        self._classifiers.append(taxonomy_classifier)

        # Signal 4: MLX-LLM Fallback (configurable via mlx.llm_* settings)
        if self._config.mlx.llm_enabled:
            mlx_llm = MLXLLMClassifier(
                enabled=True,
                model=self._config.mlx.llm_model,
                confidence_threshold=self._config.mlx.llm_confidence,
                content_preview_chars=self._config.content_preview_chars,
            )
            self._classifiers.append(mlx_llm)

        self._initialized = True
        logger.info(
            "Pipeline v2.0 initialized with %d classifiers: %s",
            len(self._classifiers),
            [c.name for c in self._classifiers],
        )

    def _get_known_technologies(self) -> list[str]:
        """Get known technologies for book/document classification.

        Returns:
            List of technology names for book detection.
        """
        # Default technologies (used for both book detection and Dell-EMC docs)
        return [
            "Ansible",
            "C++",
            "Cloud",
            "Containers",
            "DevOps",
            "Docker",
            "EKS",
            "Go",
            "GPU",
            "Java",
            "JavaScript",
            "Kubernetes",
            "Linux",
            "MariaDB",
            "MySQL",
            "Network",
            "Node.js",
            "NVIDIA",
            "OpenShift",
            "Oracle",
            "PostgreSQL",
            "Python",
            "React",
            "Rust",
            "Security",
            "Shell",
            "Tanzu",
            "Terraform",
            "TypeScript",
            "VMware",
            "vSphere",
        ]

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
