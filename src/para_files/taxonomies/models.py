"""Pydantic models for taxonomy data structures.

Supports:
- documents.json: Swiss administrative document taxonomy
- thema.json: International book classification (Thema v1.6)
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from para_files.utils.filename_sanitizer import sanitize_path_component


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

        Returns path like: 3_Resources/livres/Informatique/Programmation
        """
        hierarchy = self.get_hierarchy(code_value)
        if not hierarchy:
            return "3_Resources/livres"

        # Use top 2 levels for path
        parts = ["3_Resources", "livres"]
        for code in hierarchy[:2]:
            # Clean description for filesystem using centralized sanitizer
            desc = sanitize_path_component(code.CodeDescription)
            parts.append(desc)

        return "/".join(parts)
