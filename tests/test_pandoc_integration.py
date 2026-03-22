"""Integration tests for pandoc failure modes.

Covers broken install, timeout, encoding errors, extension validation,
and non-zero exit codes. All tests use mocking — no actual pandoc required.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from para_files.utils.pandoc import ALLOWED_EXTENSIONS, extract_metadata, extract_text


class TestPandocBrokenInstall:
    """Tests for pandoc behavior when pandoc is not installed."""

    def test_extract_text_no_pandoc(self) -> None:
        """Test that extract_text returns None when pandoc is not installed."""
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=False):
            result = extract_text(Path("/test/doc.docx"))
        assert result is None

    def test_extract_metadata_no_pandoc(self) -> None:
        """Test that extract_metadata returns None when pandoc is not installed."""
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=False):
            result = extract_metadata(Path("/test/doc.docx"))
        assert result is None

    @patch("para_files.utils.pandoc.shutil.which", return_value=None)
    def test_is_pandoc_available_no_binary(self, mock_which: MagicMock) -> None:
        """Test that is_pandoc_available returns False when binary is missing."""
        from para_files.utils.pandoc import is_pandoc_available

        result = is_pandoc_available()
        assert result is False
        mock_which.assert_called_once_with("pandoc")


class TestPandocTimeout:
    """Tests for pandoc timeout handling."""

    @patch(
        "para_files.utils.pandoc.subprocess.run",
        side_effect=subprocess.TimeoutExpired("pandoc", 30),
    )
    def test_run_pandoc_to_plain_timeout(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Test that _run_pandoc_to_plain returns None on timeout."""
        from para_files.utils.pandoc import _run_pandoc_to_plain

        test_file = tmp_path / "doc.docx"
        test_file.touch()

        result = _run_pandoc_to_plain(test_file, "docx")
        assert result is None

    def test_extract_text_timeout(self, tmp_path: Path) -> None:
        """Test that extract_text returns None on subprocess timeout."""
        test_file = tmp_path / "doc.docx"
        test_file.touch()

        with (
            patch("para_files.utils.pandoc.is_pandoc_available", return_value=True),
            patch(
                "para_files.utils.pandoc.subprocess.run",
                side_effect=subprocess.TimeoutExpired("pandoc", 30),
            ),
        ):
            result = extract_text(test_file)
        assert result is None

    def test_extract_metadata_timeout(self, tmp_path: Path) -> None:
        """Test that extract_metadata returns None on subprocess timeout."""
        test_file = tmp_path / "doc.docx"
        test_file.touch()

        with (
            patch("para_files.utils.pandoc.is_pandoc_available", return_value=True),
            patch(
                "para_files.utils.pandoc.subprocess.run",
                side_effect=subprocess.TimeoutExpired("pandoc", 10),
            ),
        ):
            result = extract_metadata(test_file)
        assert result is None


class TestPandocExtensionValidation:
    """Tests for pandoc extension validation (ERR-05)."""

    def test_rejects_unsupported_extension(self) -> None:
        """Test that extract_text returns None for unsupported extensions."""
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_text(Path("/test/file.xyz"))
        assert result is None

    def test_rejects_jpg_extension(self) -> None:
        """Test that .jpg files are rejected (not a document format)."""
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_text(Path("/test/photo.jpg"))
        assert result is None

    def test_rejects_pdf_extension(self) -> None:
        """Test that .pdf files are rejected by pandoc (handled by other extractors)."""
        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_text(Path("/test/document.pdf"))
        assert result is None

    @patch("para_files.utils.pandoc.subprocess.run")
    def test_run_pandoc_rejects_unsupported_extension(self, mock_run: MagicMock) -> None:
        """Test that _run_pandoc_to_plain rejects files not in ALLOWED_EXTENSIONS."""
        from para_files.utils.pandoc import _run_pandoc_to_plain

        result = _run_pandoc_to_plain(Path("/test/file.xyz"), "plain")
        assert result is None
        # subprocess.run should NOT be called for rejected extensions
        mock_run.assert_not_called()

    def test_allowed_extensions_non_empty(self) -> None:
        """Test that ALLOWED_EXTENSIONS is non-empty and contains core formats."""
        assert len(ALLOWED_EXTENSIONS) > 0
        assert ".docx" in ALLOWED_EXTENSIONS
        assert ".html" in ALLOWED_EXTENSIONS
        assert ".epub" in ALLOWED_EXTENSIONS


class TestPandocNonZeroExit:
    """Tests for pandoc non-zero exit code handling."""

    @patch("para_files.utils.pandoc.subprocess.run")
    def test_run_pandoc_nonzero_exit_returns_none(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _run_pandoc_to_plain returns None on non-zero exit."""
        from para_files.utils.pandoc import _run_pandoc_to_plain

        test_file = tmp_path / "doc.docx"
        test_file.touch()

        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="pandoc: error reading file",
            stdout="",
        )

        result = _run_pandoc_to_plain(test_file, "docx")
        assert result is None

    @patch("para_files.utils.pandoc.subprocess.run")
    def test_extract_metadata_nonzero_exit_returns_none(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that extract_metadata returns None on pandoc non-zero exit."""
        test_file = tmp_path / "doc.docx"
        test_file.touch()

        mock_run.return_value = MagicMock(returncode=2, stderr="error", stdout="")

        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_metadata(test_file)
        assert result is None


class TestPandocEmptyOutput:
    """Tests for pandoc empty/None stdout handling."""

    @patch("para_files.utils.pandoc.subprocess.run")
    def test_run_pandoc_empty_stdout_returns_none(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Test that _run_pandoc_to_plain returns None when stdout is empty."""
        from para_files.utils.pandoc import _run_pandoc_to_plain

        test_file = tmp_path / "doc.docx"
        test_file.touch()

        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        result = _run_pandoc_to_plain(test_file, "docx")
        assert result is None

    def test_extract_text_empty_output_returns_none(self, tmp_path: Path) -> None:
        """Test that extract_text returns None when pandoc returns empty text."""
        test_file = tmp_path / "doc.docx"
        test_file.touch()

        with (
            patch("para_files.utils.pandoc.is_pandoc_available", return_value=True),
            patch("para_files.utils.pandoc._run_pandoc_to_plain", return_value=None),
        ):
            result = extract_text(test_file)
        assert result is None


class TestPandocHappyPath:
    """Tests for successful pandoc extraction (mocked happy path)."""

    @pytest.mark.parametrize("ext", [".docx", ".html", ".epub", ".odt", ".rst"])
    @patch("para_files.utils.pandoc._run_pandoc_to_plain")
    def test_extract_text_succeeds_for_allowed_extensions(
        self, mock_run: MagicMock, ext: str, tmp_path: Path
    ) -> None:
        """Test that extract_text succeeds for each core ALLOWED_EXTENSIONS entry."""
        test_file = tmp_path / f"document{ext}"
        test_file.touch()

        mock_run.return_value = "Extracted document content."

        with patch("para_files.utils.pandoc.is_pandoc_available", return_value=True):
            result = extract_text(test_file)

        assert result is not None
        assert result.text == "Extracted document content."
        assert result.char_count > 0
        assert result.word_count > 0
