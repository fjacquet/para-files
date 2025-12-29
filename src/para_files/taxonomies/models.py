"""Pydantic models for taxonomy data structures.

Supports:
- documents.json: Swiss administrative document taxonomy
- thema.json: International book classification (Thema v1.6)
"""

from __future__ import annotations

import unicodedata

from pydantic import BaseModel, Field

from para_files.utils.filename_sanitizer import sanitize_filename


def _make_short_name(description: str, max_length: int = 20) -> str:
    """Create a short, filesystem-safe name from a Thema description.

    Transforms descriptions like:
    - "Arts : généralités" → "Generalites"
    - "Informatique et traitement de l'information" → "Informatique"
    - "Radio / podcasts" → "Radio_podcasts"
    - "Fiction / romans" → "Fiction"

    Args:
        description: Full Thema CodeDescription.
        max_length: Maximum length for the short name.

    Returns:
        Short, sanitized name suitable for folder names.
    """
    if not description:
        return "Unknown"

    name = description

    # Handle colon-separated patterns: "Arts : généralités" → "Generalites"
    if " : " in name:
        # Always take part after colon (the specific part)
        name = name.split(" : ", 1)[1]

    # Handle slash-separated alternatives: "Fiction / romans" → "Fiction"
    # Take the first part (more general term)
    if " / " in name:
        name = name.split(" / ", 1)[0]

    # Remove accents for filesystem compatibility
    # é → e, ç → c, etc.
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")

    # Sanitize using centralized function (handles special chars + spaces)
    name = sanitize_filename(name, replacement="_")

    # Take first N characters, try to break at underscore
    if len(name) > max_length:
        name = name[:max_length]
        if "_" in name:
            name = name.rsplit("_", 1)[0]

    # Capitalize first letter for readability
    if name:
        name = name[0].upper() + name[1:] if len(name) > 1 else name.upper()

    return name or "Unknown"


def _make_folder_name(code: ThemaCode, max_length: int = 35) -> str:
    """Create a hybrid folder name from a Thema code.

    Format: {CodeValue}_{ShortName}
    Example: "AB_Generalites", "U_Informatique", "UBW_Web"

    Args:
        code: ThemaCode instance.
        max_length: Maximum total length for folder name.

    Returns:
        Hybrid folder name like "AB_Generalites".
    """
    code_value = code.CodeValue
    # Reserve space for code + underscore
    short_name_max = max_length - len(code_value) - 1
    short_name = _make_short_name(code.CodeDescription, max_length=short_name_max)
    return f"{code_value}_{short_name}"


# =============================================================================
# Document Taxonomy Models (documents.json)
# =============================================================================


class Issuer(BaseModel):
    """Known document issuer with pattern matching."""

    name: str = Field(..., description="Issuer display name")
    patterns: list[str] = Field(
        default_factory=list, description="Text patterns to match (case-insensitive)"
    )


class DocumentType(BaseModel):
    """Document subtype within a category."""

    sub_id: str = Field(..., description="Unique identifier within category")
    name: str = Field(..., description="Display name")
    examples: list[str] = Field(default_factory=list, description="Example documents")
    keywords: list[str] = Field(default_factory=list, description="Keywords for semantic matching")
    required_context: list[str] = Field(
        default_factory=list,
        description="Context keywords - at least one must be present for keyword match (AND logic)",
    )
    retention: str = Field(
        default="5_years", description="Retention rule key (permanent, 10_years, etc.)"
    )
    paper_required: bool = Field(default=False, description="Whether paper original is required")
    para_pattern: str | None = Field(
        default=None, description="Override pattern for this document type"
    )
    issuers: list[Issuer] = Field(
        default_factory=list, description="Known issuers for this document type"
    )


class DocumentCategory(BaseModel):
    """Top-level document category."""

    id: str = Field(..., description="Unique category ID (CAT_XX_NAME)")
    name: str = Field(..., description="Display name with number prefix")
    description: str = Field(default="", description="Category description")
    para_pattern: str = Field(..., description="Default PARA path pattern with placeholders")
    documents: list[DocumentType] = Field(
        default_factory=list, description="Document types in this category"
    )


class TaxonomyMetadata(BaseModel):
    """Metadata about the taxonomy file."""

    title: str = Field(default="")
    version: str = Field(default="1.0")
    author: str = Field(default="")
    context: str = Field(default="")
    location: str = Field(default="")
    date_generated: str = Field(default="")
    description: str = Field(default="")


class RetentionRules(BaseModel):
    """Retention rules reference with PARA mapping."""

    permanent: str = Field(default="À vie (Vital) → 3_Resources")
    retirement: str = Field(default="Jusqu'à la rente définitive + 5 ans → 4_Archives")
    ten_years: str = Field(default="Code des Obligations Art. 127 → 4_Archives", alias="10_years")
    five_years: str = Field(default="Code des Obligations Art. 128 → 4_Archives", alias="5_years")
    contract_duration: str = Field(default="Durée du contrat + 5 ans → 4_Archives")
    warranty_2_years: str = Field(default="Garantie légale → 4_Archives")

    class Config:
        populate_by_name = True


class DocumentTaxonomy(BaseModel):
    """Complete document taxonomy from documents.json."""

    taxonomy_metadata: TaxonomyMetadata = Field(default_factory=TaxonomyMetadata)
    retention_rules_reference: RetentionRules = Field(default_factory=RetentionRules)
    categories: list[DocumentCategory] = Field(default_factory=list)

    def get_category(self, category_id: str) -> DocumentCategory | None:
        """Find category by ID."""
        for cat in self.categories:
            if cat.id == category_id:
                return cat
        return None

    def get_all_issuers(self) -> list[tuple[Issuer, DocumentType, DocumentCategory]]:
        """Get all issuers with their document type and category context."""
        return [
            (issuer, doc, cat)
            for cat in self.categories
            for doc in cat.documents
            for issuer in doc.issuers
        ]

    def get_all_keywords(
        self,
    ) -> dict[str, tuple[DocumentType, DocumentCategory, list[str]]]:
        """Get keyword to document type mapping with required context.

        Returns:
            Dict mapping keyword -> (DocumentType, DocumentCategory, required_context)
        """
        result: dict[str, tuple[DocumentType, DocumentCategory, list[str]]] = {}
        for cat in self.categories:
            for doc in cat.documents:
                for keyword in doc.keywords:
                    result[keyword.lower()] = (doc, cat, doc.required_context)
        return result


# =============================================================================
# Thema Taxonomy Models (thema.json)
# =============================================================================


class ThemaCode(BaseModel):
    """Single Thema classification code."""

    CodeValue: str = Field(..., description="Thema code (e.g., 'A', 'AB', 'ABA')")
    CodeDescription: str = Field(..., description="Human-readable description")
    CodeParent: str = Field(default="", description="Parent code for hierarchy")
    CodeNotes: str | None = Field(default=None, description="Additional notes")


class ThemaTaxonomy(BaseModel):
    """Complete Thema taxonomy from thema.json."""

    codes: dict[str, ThemaCode] = Field(
        default_factory=dict, description="Code value to ThemaCode mapping"
    )

    def get_code(self, code_value: str) -> ThemaCode | None:
        """Get code by value."""
        return self.codes.get(code_value)

    def get_hierarchy(self, code_value: str) -> list[ThemaCode]:
        """Get full hierarchy from root to given code."""
        hierarchy: list[ThemaCode] = []
        current = self.codes.get(code_value)
        while current:
            hierarchy.insert(0, current)
            if current.CodeParent:
                current = self.codes.get(current.CodeParent)
            else:
                break
        return hierarchy

    def get_children(self, parent_code: str) -> list[ThemaCode]:
        """Get direct children of a code."""
        return [code for code in self.codes.values() if code.CodeParent == parent_code]

    def build_para_path(self, code_value: str) -> str:
        """Build PARA path from Thema hierarchy.

        Uses hybrid format: {CodeValue}_{ShortName} for each level.
        Example: 3_Resources/livres/U_Informatique/UB_Programmation

        Args:
            code_value: Thema code to build path for.

        Returns:
            PARA path string like "3_Resources/livres/U_Informatique/UB_Programmation"
        """
        hierarchy = self.get_hierarchy(code_value)
        if not hierarchy:
            return "3_Resources/livres"

        # Use top 2 levels for path with hybrid naming
        parts = ["3_Resources", "livres"]
        for code in hierarchy[:2]:
            folder_name = _make_folder_name(code)
            parts.append(folder_name)

        return "/".join(parts)
