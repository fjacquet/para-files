"""Classification pipeline orchestrating 6-signal cascade.

Pipeline v2.2 - Ollama/litellm migration:
1. RulesEngine (95%) - Extension/pattern based routing
2. BookDetector (92%) - ISBN detection + Thema classification
3. TaxonomyClassifier (90%) - Issuers + keywords from documents.json
4. SemanticClassifier (85%) - Ollama embedding similarity
5. ExtensionRouterClassifier (97%) - Deterministic routing by file extension
6. LLMClassifier (60%) - Optional LLM fallback via litellm/Ollama

Chains classifiers in priority order: first match wins.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

from para_files.classifiers.book_detector import BookDetector
from para_files.classifiers.extension_router import ExtensionRouterClassifier
from para_files.classifiers.llm_classifier import LLMClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.classifiers.semantic_classifier import SemanticClassifier
from para_files.classifiers.taxonomy_classifier import TaxonomyClassifier
from para_files.config import Config
from para_files.reference_tree import ReferenceTree
from para_files.taxonomies.loader import TaxonomyLoader, get_taxonomy_loader
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
    FileMetadata,
    SignalResult,
)
from para_files.utils.filename_detector import is_generic_filename
from para_files.utils.ocr_metadata import extract_metadata
from para_files.utils.smart_renamer import perform_rename, suggest_rename


if TYPE_CHECKING:
    from para_files.classifiers.base import BaseClassifier

# Minimum content length required for OCR-based renaming
_MIN_CONTENT_FOR_RENAME = 50


class ClassificationPipeline:
    """Orchestrates 6-signal classification cascade (v2.2).

    Simplified pipeline using JSON taxonomies:
    1. Rules Engine (95%) - Extension/pattern based routing
    2. Book Detector (92%, 100% with ISBN) - ISBN + Thema classification
    3. Taxonomy Classifier (90%) - Issuers + keywords from documents.json
    4. Semantic Classifier (85%) - Ollama embedding similarity via litellm
    5. Extension Router (97%) - Deterministic routing by file extension
    6. LLM Fallback (60%) - Optional LLM via litellm/Ollama

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
        self._initialized = False
        self._init_lock = threading.Lock()

    def _ensure_initialized(self) -> None:
        """Lazily initialize classifiers on first use (thread-safe)."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:  # Double-checked locking (another thread won the race)
                return  # type: ignore[unreachable]
            self._do_initialize()

    def _do_initialize(self) -> None:
        """Perform actual initialization (called under lock)."""
        # Load reference tree (for routing_rules only in v2.0)
        self._reference_tree = ReferenceTree(self._config.reference_tree_path)
        self._reference_tree.load()

        # Load taxonomy for TaxonomyClassifier
        taxonomy_loader = get_taxonomy_loader()

        # Initialize classifiers in priority order
        self._classifiers = []

        # Signal 1: Book Detector (96%, 100% with ISBN)
        # Runs FIRST to catch books before rules_engine patterns like "*Exam*"
        # Uses THEMA classification codes for book categorization
        book_detector = BookDetector(enable_isbn_lookup=True)
        self._classifiers.append(book_detector)

        # Signal 2: Rules Engine (95%) - Extension/pattern based routing
        routing_rules = self._reference_tree.get_routing_rules()
        if routing_rules:
            rules_engine = RulesEngineClassifier(routing_rules, para_root=self._config.para_root)
            self._classifiers.append(rules_engine)

        # Signal 3: Taxonomy Classifier (90%) - Issuers + keywords from documents.json
        taxonomy_classifier = TaxonomyClassifier(loader=taxonomy_loader)
        self._classifiers.append(taxonomy_classifier)

        # Signal 4: Semantic Classifier (85%) - MLX embedding similarity
        # Uses pre-computed embeddings for category descriptions
        if self._config.mlx.semantic_enabled:
            semantic_classifier = SemanticClassifier(
                loader=taxonomy_loader,
                confidence_threshold=self._config.mlx.semantic_threshold,
                enabled=True,
            )
            self._classifiers.append(semantic_classifier)

        # Signal 5: Extension Router (97%) - Deterministic routing by file extension
        # Handles media, security, scripts, and exotic types with no semantic signal
        extension_router = ExtensionRouterClassifier(config=self._config.extension_routing)
        self._classifiers.append(extension_router)

        # Signal 6: LLM Fallback (configurable via PARA_FILES_LLM_* env vars)
        if self._config.llm.enabled:
            valid_categories = self._get_valid_categories(taxonomy_loader)
            llm = LLMClassifier(
                enabled=True,
                model=self._config.llm.model,
                confidence_threshold=self._config.llm.confidence_threshold,
                content_preview_chars=self._config.content_preview_chars,
                api_base=self._config.llm.api_base,
                valid_categories=valid_categories,
                timeout=self._config.llm.timeout,
            )
            self._classifiers.append(llm)

        self._initialized = True
        logger.info(
            "Pipeline v2.2 initialized with {} classifiers: {}",
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

    @staticmethod
    def _get_valid_categories(loader: TaxonomyLoader) -> list[str]:
        """Extract valid PARA category paths from the taxonomy.

        Args:
            loader: TaxonomyLoader with loaded documents.

        Returns:
            Sorted list of unique PARA category path patterns.
        """
        docs = loader.load_documents()
        paths: set[str] = set()
        for cat in docs.categories:
            paths.add(cat.para_pattern)
            for doc_type in cat.documents:
                if doc_type.para_pattern:
                    paths.add(doc_type.para_pattern)
        # Add generic tech documentation catch-all for English PDFs
        paths.add("3_Resources/documentation/{technology}")
        return sorted(paths)

    @staticmethod
    def _get_signal_source(classifier: BaseClassifier) -> ClassificationSource:
        """Extract ClassificationSource from a classifier."""
        raw = getattr(classifier, "source", ClassificationSource.DEFAULT)
        if isinstance(raw, ClassificationSource):
            return raw
        return ClassificationSource.DEFAULT

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

        signals: list[SignalResult] = []
        winner: ClassificationResult | None = None
        winner_idx: int = len(self._classifiers)

        # Run classifiers in priority order; stop after first match
        for idx, classifier in enumerate(self._classifiers):
            signal_source = self._get_signal_source(classifier)
            try:
                result = classifier.classify(content, metadata)
                if result is not None:
                    signals.append(
                        SignalResult(
                            source=signal_source,
                            name=classifier.name,
                            score=result.confidence.value,
                            matched=True,
                        )
                    )
                    winner = result
                    winner_idx = idx
                    logger.debug(
                        "Classified by {}: {} ({:.0f}%)",
                        classifier.name,
                        result.category,
                        result.confidence.value * 100,
                    )
                    break
                signals.append(
                    SignalResult(
                        source=signal_source,
                        name=classifier.name,
                        score=0.0,
                        matched=False,
                    )
                )
            except (ValueError, TypeError, KeyError, AttributeError, ConnectionError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as e:
                logger.exception("Classifier {} failed: {}", classifier.name, e)
                signals.append(
                    SignalResult(
                        source=signal_source,
                        name=classifier.name,
                        score=0.0,
                        matched=False,
                    )
                )

        # Record skipped classifiers for verbose display
        signals.extend(
            SignalResult(
                source=self._get_signal_source(c),
                name=c.name,
                score=0.0,
                matched=False,
                skipped=True,
            )
            for c in self._classifiers[winner_idx + 1 :]
        )

        if winner is not None:
            return winner.model_copy(update={"signals": signals})

        # Default to 0_Inbox
        logger.debug("No classifier matched, defaulting to 0_Inbox")
        return ClassificationResult(
            category="0_Inbox",
            confidence=Confidence(
                value=0.0,
                source=ClassificationSource.DEFAULT,
            ),
            signals=signals,
        )

    def classify_file(self, file_path: Path) -> ClassificationResult:
        """Classify a file by path.

        If OCR renaming is enabled and the file has a generic name,
        attempts to rename it based on OCR content before classification.

        Args:
            file_path: Path to file to classify.

        Returns:
            ClassificationResult with category and confidence.
        """
        from para_files.utils.file_utils import extract_file_metadata, read_content_preview

        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)

        # Pre-classification renaming for generic PDFs
        file_path = self._maybe_rename_generic_pdf(file_path)

        # Extract metadata
        metadata = extract_file_metadata(file_path)

        # Read content preview
        content = read_content_preview(
            file_path,
            max_chars=self._config.content_preview_chars,
        )

        return self.classify(content, metadata)

    def _maybe_rename_generic_pdf(self, file_path: Path) -> Path:
        """Rename generic PDFs using OCR metadata before classification.

        If the file has a generic name (scan_001.pdf, IMG_1234.pdf, etc.)
        and OCR renaming is enabled, extracts metadata from OCR text and
        renames the file to a descriptive name.

        Args:
            file_path: Original file path

        Returns:
            New path if renamed, original path otherwise
        """
        # Early exit conditions
        should_skip = (
            not self._config.ocr_rename.enabled
            or file_path.suffix.lower() != ".pdf"
            or not is_generic_filename(file_path.name)
        )
        if should_skip:
            return file_path

        logger.debug("Generic filename detected, attempting OCR rename: {}", file_path.name)

        # Read content for OCR (will trigger OCR if needed)
        from para_files.utils.file_utils import read_content_preview

        content = read_content_preview(file_path, max_chars=5000)

        if not content or len(content.strip()) < _MIN_CONTENT_FOR_RENAME:
            logger.debug("Not enough content for OCR rename: {}", file_path.name)
            return file_path

        # Extract metadata from content
        taxonomy_loader = get_taxonomy_loader()
        metadata = extract_metadata(content, taxonomy_loader)

        # Check if we have enough confidence to rename
        if metadata.confidence < self._config.ocr_rename.min_confidence:
            logger.debug(
                "OCR metadata confidence too low ({:.2f}): {}",
                metadata.confidence,
                file_path.name,
            )
            return file_path

        # Suggest and perform rename
        new_name, confidence = suggest_rename(metadata, file_path)
        if not new_name:
            return file_path

        new_path = perform_rename(
            file_path,
            new_name,
            dry_run=self._config.ocr_rename.dry_run,
        )

        if new_path and new_path != file_path:
            logger.info(
                "OCR rename: {} → {} (confidence: {:.2f})",
                file_path.name,
                new_path.name,
                confidence,
            )
            return new_path

        return file_path

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
