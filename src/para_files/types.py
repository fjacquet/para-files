"""Core type definitions for the para-files classification system.

This module defines all Pydantic models used throughout the classification pipeline,
ensuring strict typing and validation for the 5-signal classification system.

Key models:
- ``ClassificationSource``: Enum of classifier names
- ``Confidence``: Score + source tracking
- ``SignalResult``: Per-classifier signal captured during pipeline execution
- ``ClassificationResult``: Final classification outcome with all signals attached
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ClassificationSource(str, Enum):
    """Source of a classification decision in the 4-signal pipeline."""

    VALIDATED_DB = "validated_db"  # Signal 1: 100% confidence (deprecated)
    RULES_ENGINE = "rules_engine"  # Signal 1: 95% confidence
    BOOK_DETECTOR = "book_detector"  # Signal 2: 92% confidence (100% if ISBN found)
    DOMAIN_KB = "domain_kb"  # Signal 3: 90% confidence (deprecated)
    SEMANTIC_ROUTER = "semantic_router"  # Signal 4: 85% confidence (deprecated)
    TAXONOMY_CLASSIFIER = (
        "taxonomy_classifier"  # Signal 3: 90% confidence (replaces domain_kb + semantic_router)
    )
    LLM_FALLBACK = "llm_fallback"  # Signal 4: configurable confidence
    DEFAULT = "default"  # Fallback to inbox


class Confidence(BaseModel):
    """Classification confidence with source tracking."""

    value: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    source: ClassificationSource = Field(description="Which classifier produced this result")


class Route(BaseModel):
    """A classification route with semantic utterances for matching."""

    name: str = Field(description="Unique identifier for this route")
    pattern: str = Field(
        description="Destination pattern, e.g., '4_Archives/factures/{year}/_Assurances/{issuer}'"
    )
    utterances: list[str] = Field(
        default_factory=list,
        description="Example phrases for semantic matching",
    )
    preserve_structure: bool = Field(
        default=False,
        description="Whether to preserve source directory structure",
    )
    date_format: str | None = Field(
        default=None,
        description="Date format for path expansion, e.g., 'YYYY/MM/DD'",
    )


class RuleIssuer(BaseModel):
    """Issuer definition for routing rules with pattern matching."""

    name: str = Field(description="Canonical issuer name for folder, e.g., 'Credit Agricole'")
    patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to match in content, e.g., ['Credit Agricole', 'Crédit Agricole']",
    )


class RoutingRule(BaseModel):
    """Special routing rule for specific file types (photos, videos, courses)."""

    source: str | None = Field(
        default=None,
        description="Source directory to watch, e.g., '0_Inbox'",
    )
    extensions: list[str] = Field(
        default_factory=list,
        description="File extensions to match, e.g., ['.jpg', '.png']",
    )
    patterns: list[str] = Field(
        default_factory=list,
        description="Glob patterns to match, e.g., ['Screenshot*', 'Capture*']",
    )
    destination: str = Field(description="Destination pattern with placeholders")
    date_source: str | None = Field(
        default=None,
        description="Where to get date from: 'exif', 'filename', 'content', or 'file_modified'",
    )
    fallback_date: str | None = Field(
        default=None,
        description="Fallback date source if primary fails",
    )
    date_pattern: str | None = Field(
        default=None,
        description="Regex pattern for extracting date from filename",
    )
    action: str | None = Field(
        default=None,
        description="Special action: 'preserve_structure', 'flatten_to_inbox'",
    )
    platforms: dict[str, list[str]] | None = Field(
        default=None,
        description="Platform-specific patterns for courses",
    )
    issuers: list[RuleIssuer] = Field(
        default_factory=list,
        description="List of issuers for {issuer} placeholder resolution",
    )
    known_technologies: list[str] = Field(
        default_factory=list,
        description="Known technologies for {technology} placeholder resolution",
    )
    auto_correct_date: bool = Field(
        default=False,
        description="Rename file when filename date differs from content date",
    )


class CategoryNode(BaseModel):
    """Node in the PARA category hierarchy."""

    path: str = Field(description="Full path from PARA root")
    behavior: str | None = Field(default=None, description="Special behavior, e.g., 'flat'")
    description: str | None = Field(default=None, description="Human-readable description")
    routes: list[Route] = Field(default_factory=list, description="Routes under this category")


class SignalResult(BaseModel):
    """Per-classifier signal result captured during pipeline execution."""

    source: ClassificationSource = Field(description="Which classifier produced this entry")
    name: str = Field(description="Human-readable classifier name, e.g., 'rules_engine'")
    score: float = Field(description="Confidence score returned (0.0 if classifier skipped)")
    matched: bool = Field(description="True if this classifier returned a non-None result")


class ClassificationResult(BaseModel):
    """Result of classifying a file or content through the pipeline."""

    category: str = Field(
        description="Resolved category path, e.g., '4_Archives/factures/2025/_Assurances/Swica'"
    )
    confidence: Confidence = Field(description="Confidence score and source")
    route_name: str | None = Field(
        default=None,
        description="Name of the matched route, if any",
    )
    extracted_params: dict[str, str] = Field(
        default_factory=dict,
        description="Extracted parameters from content, e.g., {'year': '2025', 'issuer': 'Swica'}",
    )
    raw_score: float | None = Field(
        default=None,
        description="Raw similarity score from semantic router",
    )
    signals: list[SignalResult] = Field(
        default_factory=list,
        description="Per-classifier signal results collected during pipeline execution",
    )


class FileMetadata(BaseModel):
    """Metadata extracted from a file for classification."""

    path: Path = Field(description="Absolute path to the file")
    filename: str = Field(description="Filename without directory")
    extension: str = Field(description="File extension including dot, e.g., '.pdf'")
    size_bytes: int = Field(ge=0, description="File size in bytes")
    created_at: datetime | None = Field(default=None, description="File creation timestamp")
    modified_at: datetime | None = Field(default=None, description="Last modification timestamp")
    content_preview: str | None = Field(
        default=None,
        description="First N characters of content for semantic matching",
    )

    # EXIF metadata (extracted via exiftool)
    exif_date: datetime | None = Field(
        default=None,
        description="Date from EXIF (DateTimeOriginal or CreateDate)",
    )
    exif_gps_lat: float | None = Field(
        default=None,
        description="GPS latitude in decimal degrees",
    )
    exif_gps_lon: float | None = Field(
        default=None,
        description="GPS longitude in decimal degrees",
    )
    exif_camera: str | None = Field(
        default=None,
        description="Camera make and model",
    )

    # PDF metadata (extracted via pypdf)
    pdf_title: str | None = Field(
        default=None,
        description="PDF document title from metadata",
    )
    pdf_author: str | None = Field(
        default=None,
        description="PDF document author from metadata",
    )
    pdf_subject: str | None = Field(
        default=None,
        description="PDF document subject from metadata",
    )

    model_config = {"arbitrary_types_allowed": True}

    @property
    def best_date(self) -> datetime | None:
        """Return the best available date for path resolution.

        Priority: EXIF date > file modified > file created.
        """
        return self.exif_date or self.modified_at or self.created_at


class IssuerCategory(BaseModel):
    """A category of issuers with its destination pattern."""

    pattern: str = Field(
        default="4_Archives/factures/{year}/_Other/{issuer}",
        description="Path pattern with {year} and {issuer} placeholders",
    )
    issuers: list[str] = Field(default_factory=list)


class KnownIssuers(BaseModel):
    """Database of known issuers organized by category.

    Categories are loaded dynamically from YAML - no hardcoded fields.
    Each category has a pattern and list of issuer names.
    """

    categories: dict[str, IssuerCategory] = Field(default_factory=dict)

    def all_issuers(self) -> dict[str, str]:
        """Return a mapping of issuer name (lowercase) to category."""
        result: dict[str, str] = {}
        for category_name, category in self.categories.items():
            for issuer in category.issuers:
                result[issuer.lower()] = category_name
        return result

    def get_pattern(self, category: str) -> str:
        """Get path pattern for a category.

        Args:
            category: Category name.

        Returns:
            Path pattern string, or default pattern if category not found.
        """
        if category in self.categories:
            return self.categories[category].pattern
        return f"4_Archives/factures/{{year}}/_Other/{category}"

    def get_issuers(self, category: str) -> list[str]:
        """Get issuers for a category.

        Args:
            category: Category name.

        Returns:
            List of issuer names, or empty list if category not found.
        """
        if category in self.categories:
            return self.categories[category].issuers
        return []

    def list_categories(self) -> list[str]:
        """Return list of all category names."""
        return list(self.categories.keys())


class ReferenceTreeData(BaseModel):
    """Complete reference tree loaded from YAML."""

    version: str = Field(description="Schema version")
    generated: str | None = Field(default=None, description="Generation date")
    routing_rules: dict[str, Any] = Field(
        default_factory=dict,
        description="Special routing rules (photos, videos, courses)",
    )
    inbox: CategoryNode | None = Field(default=None, description="0_Inbox configuration")
    projects: CategoryNode | None = Field(default=None, description="1_Projects configuration")
    areas: CategoryNode | None = Field(default=None, description="2_Areas configuration")
    resources: CategoryNode | None = Field(default=None, description="3_Resources configuration")
    archives: CategoryNode | None = Field(default=None, description="4_Archives configuration")
    known_issuers: KnownIssuers = Field(
        default_factory=KnownIssuers,
        description="Database of known issuers by category",
    )
