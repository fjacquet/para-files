"""Taxonomy loader with caching support.

Loads documents.json and thema.json with lazy loading and caching.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from para_files.taxonomies.models import (
    DocumentCategory,
    DocumentTaxonomy,
    DocumentType,
    Issuer,
    RetentionRules,
    TaxonomyMetadata,
    ThemaCode,
    ThemaTaxonomy,
)


class TaxonomyLoader:
    """Load and cache taxonomy files."""

    def __init__(
        self,
        documents_path: Path | str | None = None,
        thema_path: Path | str | None = None,
    ) -> None:
        """Initialize loader with optional custom paths.

        Args:
            documents_path: Path to documents.json (default: config/documents.json)
            thema_path: Path to thema.json (default: config/thema.json)
        """
        self._documents_path = Path(documents_path) if documents_path else None
        self._thema_path = Path(thema_path) if thema_path else None
        self._documents: DocumentTaxonomy | None = None
        self._thema: ThemaTaxonomy | None = None

    @staticmethod
    def _find_config_dir() -> Path:
        """Find the config directory relative to the project."""
        # Try common locations
        candidates = [
            Path.cwd() / "config",
            Path(__file__).parent.parent.parent.parent / "config",
        ]
        for path in candidates:
            if path.exists():
                return path
        return Path.cwd() / "config"

    def _get_documents_path(self) -> Path:
        """Get the documents.json path."""
        if self._documents_path:
            return self._documents_path
        return self._find_config_dir() / "documents.json"

    def _get_thema_path(self) -> Path:
        """Get the thema.json path."""
        if self._thema_path:
            return self._thema_path
        return self._find_config_dir() / "thema.json"

    def load_documents(self, *, force_reload: bool = False) -> DocumentTaxonomy:
        """Load document taxonomy from JSON.

        Args:
            force_reload: Force reload even if cached

        Returns:
            DocumentTaxonomy with all categories and issuers
        """
        if self._documents is not None and not force_reload:
            return self._documents

        path = self._get_documents_path()
        if not path.exists():
            # Return empty taxonomy if file doesn't exist
            self._documents = DocumentTaxonomy()
            return self._documents

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Parse metadata
        metadata = TaxonomyMetadata(**data.get("taxonomy_metadata", {}))

        # Parse retention rules
        retention = RetentionRules(**data.get("retention_rules_reference", {}))

        # Parse categories
        categories: list[DocumentCategory] = []
        for cat_data in data.get("categories", []):
            documents: list[DocumentType] = []
            for doc_data in cat_data.get("documents", []):
                # Parse issuers
                issuers = [Issuer(**issuer_data) for issuer_data in doc_data.get("issuers", [])]
                doc = DocumentType(
                    sub_id=doc_data["sub_id"],
                    name=doc_data.get("name", ""),
                    examples=doc_data.get("examples", []),
                    keywords=doc_data.get("keywords", []),
                    required_context=doc_data.get("required_context", []),
                    retention=doc_data.get("retention", "5_years"),
                    paper_required=doc_data.get("paper_required", False),
                    para_pattern=doc_data.get("para_pattern"),
                    issuers=issuers,
                )
                documents.append(doc)

            category = DocumentCategory(
                id=cat_data["id"],
                name=cat_data.get("name", ""),
                description=cat_data.get("description", ""),
                para_pattern=cat_data.get("para_pattern", "4_Archives"),
                documents=documents,
            )
            categories.append(category)

        self._documents = DocumentTaxonomy(
            taxonomy_metadata=metadata,
            retention_rules_reference=retention,
            categories=categories,
        )
        return self._documents

    def load_thema(self, *, force_reload: bool = False) -> ThemaTaxonomy:
        """Load Thema taxonomy from JSON.

        Args:
            force_reload: Force reload even if cached

        Returns:
            ThemaTaxonomy with all codes
        """
        if self._thema is not None and not force_reload:
            return self._thema

        path = self._get_thema_path()
        if not path.exists():
            self._thema = ThemaTaxonomy()
            return self._thema

        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        # Thema JSON structure: CodeList.ThemaCodes.Code[]
        codes: dict[str, ThemaCode] = {}
        code_list = data.get("CodeList", {}).get("ThemaCodes", {}).get("Code", [])

        for code_data in code_list:
            # Handle CodeParent which can be string, int, or empty
            parent = code_data.get("CodeParent", "")
            if isinstance(parent, int):
                parent = str(parent)
            code = ThemaCode(
                CodeValue=str(code_data.get("CodeValue", "")),
                CodeDescription=code_data.get("CodeDescription", ""),
                CodeParent=parent,
                CodeNotes=code_data.get("CodeNotes"),
            )
            codes[code.CodeValue] = code

        self._thema = ThemaTaxonomy(codes=codes)
        return self._thema

    def reload_all(self) -> None:
        """Force reload all taxonomies."""
        self._documents = None
        self._thema = None
        self.load_documents(force_reload=True)
        self.load_thema(force_reload=True)


# Global cached loader instance
@lru_cache(maxsize=1)
def get_taxonomy_loader() -> TaxonomyLoader:
    """Get or create the global taxonomy loader instance."""
    return TaxonomyLoader()
