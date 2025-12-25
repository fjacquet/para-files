"""Tests for the main module."""

from __future__ import annotations

from para_files import __version__, main


def test_version():
    """Verify package version is set."""
    assert __version__ == "0.1.0"


def test_main_runs(capsys):
    """Verify main function executes without error."""
    main()
    captured = capsys.readouterr()
    assert "para-files" in captured.out.lower()
