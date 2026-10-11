"""Repository hygiene: personal config must not be tracked (spec S6)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
GIT = shutil.which("git")


@pytest.mark.skipif(GIT is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
def test_personal_reference_tree_is_not_tracked():
    assert GIT is not None
    tracked = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", "config/personal_file_tree.yaml"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert tracked.strip() == ""


@pytest.mark.skipif(GIT is None or not (ROOT / ".git").exists(), reason="needs a git checkout")
@pytest.mark.parametrize("path", [".serena", ".claude", ".planning", "TODO-routing-fixes.md"])
def test_tool_state_and_old_notes_are_not_tracked(path: str):
    assert GIT is not None
    tracked = subprocess.run(  # noqa: S603 - fixed git command, no user input
        [GIT, "ls-files", path], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout
    assert tracked.strip() == ""
