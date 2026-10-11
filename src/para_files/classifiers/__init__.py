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

from __future__ import annotations

import importlib
from typing import Any


_EXPORTS = {
    "BaseClassifier": "base",
    "BookDetector": "book_detector",
    "ExtensionRouterClassifier": "extension_router",
    "LLMClassifier": "llm_classifier",
    "RulesEngineClassifier": "rules_engine",
    "SemanticClassifier": "semantic_classifier",
    "TaxonomyClassifier": "taxonomy_classifier",
}


__all__ = [
    "BaseClassifier",
    "BookDetector",
    "ExtensionRouterClassifier",
    "LLMClassifier",
    "RulesEngineClassifier",
    "SemanticClassifier",
    "TaxonomyClassifier",
]


def __getattr__(name: str) -> Any:  # noqa: ANN401 - any exported class
    """Import a classifier on first use, so importing one submodule stays light."""
    if name not in _EXPORTS:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)
    return getattr(importlib.import_module(f"{__name__}.{_EXPORTS[name]}"), name)
