"""Tests for Thema taxonomy models and path building."""

from __future__ import annotations

from para_files.taxonomies.models import (
    ThemaCode,
    ThemaTaxonomy,
    _make_folder_name,
    _make_short_name,
)


class TestMakeShortName:
    """Tests for _make_short_name helper function."""

    def test_simple_name(self) -> None:
        """Simple name is preserved."""
        assert _make_short_name("Arts") == "Arts"

    def test_removes_colon_prefix(self) -> None:
        """Removes category prefix before colon."""
        result = _make_short_name("Arts : généralités")
        assert result == "Generalites"

    def test_handles_slash_alternatives(self) -> None:
        """Takes first part of slash-separated alternatives."""
        result = _make_short_name("Radio / podcasts")
        assert result == "Radio"

    def test_removes_accents(self) -> None:
        """Removes accents for filesystem compatibility."""
        result = _make_short_name("Éducation française")
        assert "é" not in result.lower()
        assert "ç" not in result.lower()
        assert result == "Education_francaise"

    def test_truncates_long_names(self) -> None:
        """Truncates long names to max_length."""
        long_name = "Informatique et traitement de l'information"
        result = _make_short_name(long_name, max_length=15)
        assert len(result) <= 15

    def test_empty_returns_unknown(self) -> None:
        """Empty string returns Unknown."""
        assert _make_short_name("") == "Unknown"

    def test_capitalizes_first_letter(self) -> None:
        """First letter is capitalized."""
        result = _make_short_name("programmation")
        assert result[0].isupper()


class TestMakeFolderName:
    """Tests for _make_folder_name helper function."""

    def test_simple_code(self) -> None:
        """Simple code produces hybrid format."""
        code = ThemaCode(CodeValue="A", CodeDescription="Arts")
        result = _make_folder_name(code)
        assert result == "A_Arts"

    def test_subcategory_code(self) -> None:
        """Subcategory uses suffix after colon."""
        code = ThemaCode(CodeValue="AB", CodeDescription="Arts : généralités")
        result = _make_folder_name(code)
        assert result == "AB_Generalites"

    def test_informatique_code(self) -> None:
        """Informatique category works correctly."""
        code = ThemaCode(
            CodeValue="U",
            CodeDescription="Informatique et traitement de l'information",
        )
        result = _make_folder_name(code)
        assert result.startswith("U_")
        assert "Informatique" in result

    def test_max_length_respected(self) -> None:
        """Max length is respected."""
        code = ThemaCode(
            CodeValue="ABCD",
            CodeDescription="Very long description that should be truncated",
        )
        result = _make_folder_name(code, max_length=20)
        assert len(result) <= 20
        assert result.startswith("ABCD_")


class TestThemaTaxonomyBuildParaPath:
    """Tests for ThemaTaxonomy.build_para_path method."""

    def test_empty_hierarchy(self) -> None:
        """Unknown code returns default path."""
        taxonomy = ThemaTaxonomy(codes={})
        result = taxonomy.build_para_path("UNKNOWN")
        assert result == "3_Resources/livres"

    def test_single_level(self) -> None:
        """Single level code produces correct path."""
        taxonomy = ThemaTaxonomy(
            codes={
                "A": ThemaCode(CodeValue="A", CodeDescription="Arts"),
            }
        )
        result = taxonomy.build_para_path("A")
        assert result == "3_Resources/livres/A_Arts"

    def test_two_levels(self) -> None:
        """Two level hierarchy produces correct path."""
        taxonomy = ThemaTaxonomy(
            codes={
                "A": ThemaCode(CodeValue="A", CodeDescription="Arts"),
                "AB": ThemaCode(
                    CodeValue="AB", CodeDescription="Arts : généralités", CodeParent="A"
                ),
            }
        )
        result = taxonomy.build_para_path("AB")
        assert result == "3_Resources/livres/A_Arts/AB_Generalites"

    def test_three_levels_uses_only_two(self) -> None:
        """Three level hierarchy only uses top 2 levels."""
        taxonomy = ThemaTaxonomy(
            codes={
                "A": ThemaCode(CodeValue="A", CodeDescription="Arts"),
                "AB": ThemaCode(
                    CodeValue="AB", CodeDescription="Arts : généralités", CodeParent="A"
                ),
                "ABA": ThemaCode(
                    CodeValue="ABA", CodeDescription="Théorie de l'art", CodeParent="AB"
                ),
            }
        )
        result = taxonomy.build_para_path("ABA")
        # Should only have 2 levels after livres
        parts = result.split("/")
        assert len(parts) == 4  # 3_Resources, livres, A_Arts, AB_Generalites
        assert parts[0] == "3_Resources"
        assert parts[1] == "livres"
        assert parts[2] == "A_Arts"
        assert parts[3] == "AB_Generalites"

    def test_informatique_hierarchy(self) -> None:
        """Informatique hierarchy produces correct path."""
        taxonomy = ThemaTaxonomy(
            codes={
                "U": ThemaCode(
                    CodeValue="U",
                    CodeDescription="Informatique et traitement de l'information",
                ),
                "UB": ThemaCode(
                    CodeValue="UB",
                    CodeDescription="Informatique : logiciels et programmation",
                    CodeParent="U",
                ),
            }
        )
        result = taxonomy.build_para_path("UB")
        assert "3_Resources/livres/" in result
        assert "U_" in result
        assert "UB_" in result

    def test_no_special_chars_in_path(self) -> None:
        """Path contains no invalid filesystem characters."""
        taxonomy = ThemaTaxonomy(
            codes={
                "X": ThemaCode(CodeValue="X", CodeDescription="Test: with / special < chars"),
            }
        )
        result = taxonomy.build_para_path("X")
        invalid_chars = [":", "/", "\\", "<", ">", '"', "|", "?", "*", "#", ","]
        # Skip the path separator /
        path_without_sep = result.replace("3_Resources/livres/", "")
        for char in invalid_chars:
            assert char not in path_without_sep, f"Found invalid char '{char}' in path"
