"""analyze_inbox defaults to the same reference tree the classifier uses."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest


def test_config_option_defaults_to_personal_tree(
    load_script: Callable[[str], ModuleType], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a personal tree in $PARA_FILES_CONFIG_DIR, the --config default points at it."""
    config_dir = tmp_path / "personal"
    config_dir.mkdir()
    personal = config_dir / "personal_file_tree.yaml"
    personal.write_text("routing_rules: {}\n")
    monkeypatch.setenv("PARA_FILES_CONFIG_DIR", str(config_dir))

    module = load_script("analyze_inbox")
    option = next(p for p in module.main.params if p.name == "config")

    assert option.default == personal
