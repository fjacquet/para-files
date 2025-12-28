"""Taxonomy models and loaders for para-files classification.

This module provides:
- Pydantic models for documents.json and thema.json
- TaxonomyLoader for loading and caching taxonomies
"""

from __future__ import annotations

from para_files.taxonomies.loader import TaxonomyLoader
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


__all__ = [
    "DocumentCategory",
    "DocumentTaxonomy",
    "DocumentType",
    "Issuer",
    "RetentionRules",
    "TaxonomyLoader",
    "TaxonomyMetadata",
    "ThemaCode",
    "ThemaTaxonomy",
]
