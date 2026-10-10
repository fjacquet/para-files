"""Safety tests for the move command (Stage 0)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from para_files.cli.move_cmd import _handle_move_file
from para_files.mover import ConflictStrategy


def test_ctrl_c_during_classification_aborts_and_leaves_file(tmp_path: Path) -> None:
    """Ctrl+C while classifying stops the run; the file is not moved anywhere."""
    source = tmp_path / "doc.txt"
    source.write_text("content")

    pipeline = MagicMock()
    pipeline.classify_file.side_effect = KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _handle_move_file(
            source,
            pipeline,
            [],
            "Moved",
            dry_run=False,
            copy=False,
            conflict_strategy=ConflictStrategy.RENAME,
            date_prefix=False,
            smart_rename=False,
            output_json=False,
        )

    assert source.exists()
    pipeline.get_target_path.assert_not_called()
