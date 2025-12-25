"""Tests for the main module."""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from para_files import __version__, main


def test_version():
    """Verify package version is set."""
    assert __version__ == "0.1.0"


def test_main_help(capsys):
    """Verify main function shows help."""
    with patch.object(sys, "argv", ["para-files", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "para-files" in captured.out.lower()


def test_main_classify_missing_path(capsys):
    """Verify main function errors on missing file path."""
    with patch.object(sys, "argv", ["para-files", "classify"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        # Should fail because no file path provided
        assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "error" in captured.err.lower()
