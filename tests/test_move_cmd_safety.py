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


def test_parallel_move_keeps_same_named_files(tmp_path: Path) -> None:
    """A parallel `move` of six different files named alike keeps all six."""
    from para_files.cli.move_cmd import _move_files_parallel
    from para_files.types import ClassificationResult, ClassificationSource, Confidence

    target = tmp_path / "para" / "3_Resources" / "test"
    files = []
    for i in range(6):
        folder = tmp_path / f"in{i}"
        folder.mkdir()
        f = folder / "same.txt"
        f.write_text(f"payload {i}")
        files.append(f)

    pipeline = MagicMock()
    pipeline.classify_file.return_value = ClassificationResult(
        category="3_Resources/test",
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )
    pipeline.get_target_path.return_value = target

    _, _, success, skipped, failed = _move_files_parallel(
        files,
        pipeline,
        4,
        dry_run=False,
        copy=False,
        conflict_strategy=ConflictStrategy.RENAME,
        date_prefix=False,
        smart_rename=False,
        skip_unclassifiable=False,
        output_json=True,
        action_verb="Moved",
    )

    assert (success, skipped, failed) == (6, 0, 0)
    contents = sorted(p.read_text() for p in target.iterdir())
    assert contents == sorted(f"payload {i}" for i in range(6))


def test_ctrl_c_in_parallel_move_stops_queued_files(tmp_path: Path) -> None:
    """Default parallel path: Ctrl+C after the first result leaves queued files unprocessed."""
    import time
    from concurrent.futures import as_completed as real_as_completed
    from unittest.mock import patch

    from para_files.cli.move_cmd import _move_files_parallel
    from para_files.types import ClassificationResult, ClassificationSource, Confidence

    files = []
    for i in range(40):
        f = tmp_path / f"f{i}.txt"
        f.write_text(str(i))
        files.append(f)

    def slow_classify(_path: Path) -> ClassificationResult:
        time.sleep(0.05)
        return ClassificationResult(
            category="3_Resources/test",
            confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
        )

    pipeline = MagicMock()
    pipeline.classify_file.side_effect = slow_classify
    pipeline.get_target_path.return_value = tmp_path / "para" / "3_Resources" / "test"

    def interrupting(fs, timeout=None):
        it = real_as_completed(fs, timeout)
        yield next(it)
        raise KeyboardInterrupt

    with (
        patch("para_files.cli.move_cmd.as_completed", side_effect=interrupting),
        pytest.raises(KeyboardInterrupt),
    ):
        _move_files_parallel(
            files,
            pipeline,
            4,
            dry_run=True,
            copy=False,
            conflict_strategy=ConflictStrategy.RENAME,
            date_prefix=False,
            smart_rename=False,
            skip_unclassifiable=False,
            output_json=True,
            action_verb="Would move",
        )

    assert pipeline.classify_file.call_count <= 8
