"""Classification signals for the 6-signal pipeline (v2.1).

Pipeline signals in priority order:
1. RulesEngine (95%) - Extension/pattern based routing
2. BookDetector (92%) - ISBN detection + Thema classification
3. TaxonomyClassifier (90%) - Issuers + keywords from documents.json
4. SemanticClassifier (85%) - Ollama embedding similarity
5. ExtensionRouterClassifier (97%) - Deterministic routing by file extension
6. LLMClassifier (60%) - Optional LLM fallback via litellm/Ollama

First match wins. Default to 0_Inbox if no match.
"""

from para_files.classifiers.base import BaseClassifier
from para_files.classifiers.book_detector import BookDetector
from para_files.classifiers.extension_router import ExtensionRouterClassifier
from para_files.classifiers.llm_classifier import LLMClassifier
from para_files.classifiers.rules_engine import RulesEngineClassifier
from para_files.classifiers.semantic_classifier import SemanticClassifier
from para_files.classifiers.taxonomy_classifier import TaxonomyClassifier


__all__ = [
    "BaseClassifier",
    "BookDetector",
    "ExtensionRouterClassifier",
    "LLMClassifier",
    "RulesEngineClassifier",
    "SemanticClassifier",
    "TaxonomyClassifier",
]
