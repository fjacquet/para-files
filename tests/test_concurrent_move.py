"""Tests for concurrent file move threading safety (TEST-03)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from para_files.cli.move_cmd import _move_files_parallel, _move_files_sequential
from para_files.mover import ConflictStrategy
from para_files.types import ClassificationResult, ClassificationSource, Confidence


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(dest: str) -> ClassificationResult:
    """Create a minimal ClassificationResult for testing."""
    return ClassificationResult(
        category=dest,
        confidence=Confidence(value=0.9, source=ClassificationSource.RULES_ENGINE),
    )


def _build_mock_pipeline(tmp_path: Path, category: str = "3_Resources/test") -> MagicMock:
    """Build a mock pipeline that classifies all files to a tmp destination."""
    mock_pipeline = MagicMock()
    mock_pipeline.classify_file.return_value = _make_result(category)
    # get_target_path must return a real Path so FileMover can compute destination
    mock_pipeline.get_target_path.return_value = tmp_path / category
    return mock_pipeline


def _create_files(tmp_path: Path, count: int) -> list[Path]:
    """Create *count* real text files in *tmp_path*."""
    files = []
    for i in range(count):
        p = tmp_path / f"file_{i}.txt"
        p.write_text(f"content_{i}")
        files.append(p)
    return files


_PARALLEL_KWARGS: dict = {
    "dry_run": True,
    "copy": False,
    "conflict_strategy": ConflictStrategy.SKIP,
    "date_prefix": False,
    "smart_rename": False,
    "skip_unclassifiable": False,
    "output_json": False,
    "action_verb": "Would move",
    "verbose": False,
}

_SEQUENTIAL_KWARGS: dict = {
    "dry_run": True,
    "copy": False,
    "conflict_strategy": ConflictStrategy.SKIP,
    "date_prefix": False,
    "smart_rename": False,
    "skip_unclassifiable": False,
    "enable_rollback": False,
    "output_json": False,
    "action_verb": "Would move",
    "verbose": False,
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_crashing_worker_others_succeed(tmp_path: Path) -> None:
    """One worker crashing on a specific file does not lose the other 4 results."""
    files = _create_files(tmp_path, 5)
    crash_file = files[2]  # exactly one file will crash

    mock_pipeline = _build_mock_pipeline(tmp_path)

    def crash_on_specific_file(file_path: Path) -> ClassificationResult:
        if file_path.name == crash_file.name:
            msg = "simulated worker crash"
            raise RuntimeError(msg)
        return _make_result("3_Resources/test")

    mock_pipeline.classify_file.side_effect = crash_on_specific_file

    *_, success_count, skip_count, fail_count = _move_files_parallel(
        expanded_files=files,
        pipeline=mock_pipeline,
        max_workers=2,
        **_PARALLEL_KWARGS,
    )

    total = success_count + skip_count + fail_count
    assert total == 5, f"Expected 5 total results, got {total}"
    assert fail_count == 1, f"Expected exactly 1 failure, got {fail_count}"
    assert success_count >= 4, f"Expected at least 4 successes, got {success_count}"


def test_load_ten_files_no_silent_losses(tmp_path: Path) -> None:
    """10-file load test: all 10 files are accounted for, no silent losses."""
    files = _create_files(tmp_path, 10)
    mock_pipeline = _build_mock_pipeline(tmp_path)

    *_, success_count, skip_count, fail_count = _move_files_parallel(
        expanded_files=files,
        pipeline=mock_pipeline,
        max_workers=4,
        **_PARALLEL_KWARGS,
    )

    total = success_count + skip_count + fail_count
    assert total == 10, f"Expected 10 total results, got {total}"
    assert fail_count == 0, f"Expected 0 failures, got {fail_count}"
    assert success_count == 10, f"Expected 10 successes, got {success_count}"


def test_single_vs_parallel_same_results(tmp_path: Path) -> None:
    """Sequential and parallel execution process the same set of source files."""
    files = _create_files(tmp_path, 6)
    mock_pipeline = _build_mock_pipeline(tmp_path)

    _, seq_success, seq_skip, seq_fail = _move_files_sequential(
        expanded_files=files,
        pipeline=mock_pipeline,
        source_dirs=set(),
        **_SEQUENTIAL_KWARGS,
    )

    *_, par_success, par_skip, par_fail = _move_files_parallel(
        expanded_files=files,
        pipeline=mock_pipeline,
        max_workers=4,
        **_PARALLEL_KWARGS,
    )

    seq_total = seq_success + seq_skip + seq_fail
    par_total = par_success + par_skip + par_fail

    assert seq_total == 6, f"Sequential processed {seq_total} files, expected 6"
    assert par_total == 6, f"Parallel processed {par_total} files, expected 6"
    assert seq_total == par_total, "Sequential and parallel must process the same number of files"
    assert seq_fail == 0, f"Sequential had {seq_fail} failures"
    assert par_fail == 0, f"Parallel had {par_fail} failures"
