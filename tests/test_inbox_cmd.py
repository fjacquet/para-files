"""TDD test suite for the inbox CLI command.

Verifies all four UX requirements:
- UX-01: Single-command operation — confident files are moved to PARA destination
- UX-02: Inbox-safe failure — DEFAULT-classified files stay in inbox (not moved)
- UX-03: Real-time progress display — output contains [idx/total] prefix and destination
- UX-04: Post-run summary — output contains total, moved, stayed, and by-signal breakdown

Test classes:
- TestInboxStats: unit tests for _InboxStats dataclass
- TestProcessInboxFile: unit tests for _process_inbox_file function
- TestPrintInboxSummary: unit tests for _print_inbox_summary function
- TestInboxCommand: integration tests via CliRunner
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from para_files.cli.app import app
from para_files.cli.inbox_cmd import (
    _InboxStats,
    _print_inbox_summary,
    _process_inbox_file,
)
from para_files.mover import ConflictStrategy, MoveResult
from para_files.types import (
    ClassificationResult,
    ClassificationSource,
    Confidence,
)


# ---------------------------------------------------------------------------
# TestInboxStats — unit tests for _InboxStats dataclass
# ---------------------------------------------------------------------------


class TestInboxStats:
    """Unit tests for the _InboxStats dataclass."""

    def test_defaults(self) -> None:
        """Verify default values: total=0, moved=0, stayed=0, failed=0, by_signal={}."""
        stats = _InboxStats()

        assert stats.total == 0
        assert stats.moved == 0
        assert stats.stayed == 0
        assert stats.failed == 0
        assert stats.by_signal == {}

    def test_total_can_be_set_at_construction(self) -> None:
        """Verify total can be set at construction time."""
        stats = _InboxStats(total=5)

        assert stats.total == 5
        assert stats.moved == 0
        assert stats.stayed == 0
        assert stats.failed == 0

    def test_by_signal_is_independent_per_instance(self) -> None:
        """Verify by_signal dicts are not shared between instances (default_factory)."""
        stats_a = _InboxStats()
        stats_b = _InboxStats()
        stats_a.by_signal["rules_engine"] = 3

        assert stats_b.by_signal == {}


# ---------------------------------------------------------------------------
# TestProcessInboxFile — unit tests for _process_inbox_file
# ---------------------------------------------------------------------------


class TestProcessInboxFile:
    """Unit tests for _process_inbox_file using mocked pipeline and mover."""

    def _make_result(
        self, source: ClassificationSource, confidence: float = 0.95
    ) -> ClassificationResult:
        """Build a ClassificationResult with the given source."""
        return ClassificationResult(
            category="3_Resources/tests",
            confidence=Confidence(value=confidence, source=source),
        )

    def _make_file(self, tmp_path: Path, name: str = "test.txt") -> Path:
        """Create a dummy file in tmp_path."""
        f = tmp_path / name
        f.write_text("dummy content")
        return f

    def test_confidently_classified_file_is_moved(self, tmp_path: Path) -> None:
        """UX-01: A confidently classified file (RULES_ENGINE) must be moved and stats updated."""
        file_path = self._make_file(tmp_path)
        pipeline = MagicMock()
        pipeline.classify_file.return_value = self._make_result(ClassificationSource.RULES_ENGINE)
        pipeline.get_target_path.return_value = tmp_path / "3_Resources" / "tests"

        success_result = MoveResult(
            source=file_path,
            destination=tmp_path / "3_Resources" / "tests" / "test.txt",
            success=True,
            action="moved",
            message="",
        )

        stats = _InboxStats(total=3)

        with patch("para_files.cli.inbox_cmd.move_classified_file", return_value=success_result):
            _process_inbox_file(
                file_path,
                pipeline,
                stats,
                idx=1,
                total=3,
                dry_run=False,
                conflict_strategy=ConflictStrategy.RENAME,
                verbose=False,
            )

        assert stats.moved == 1
        assert stats.stayed == 0
        assert stats.by_signal.get("rules_engine") == 1

    def test_default_classified_file_stays(self, tmp_path: Path) -> None:
        """UX-02: A DEFAULT-classified file must stay in inbox — move_classified_file NOT called."""
        file_path = self._make_file(tmp_path)
        pipeline = MagicMock()
        pipeline.classify_file.return_value = self._make_result(ClassificationSource.DEFAULT)

        stats = _InboxStats(total=3)

        with patch("para_files.cli.inbox_cmd.move_classified_file") as mock_mover:
            _process_inbox_file(
                file_path,
                pipeline,
                stats,
                idx=1,
                total=3,
                dry_run=False,
                conflict_strategy=ConflictStrategy.RENAME,
                verbose=False,
            )

        assert stats.stayed == 1
        assert stats.moved == 0
        mock_mover.assert_not_called()

    def test_pipeline_exception_increments_failed(self, tmp_path: Path) -> None:
        """When pipeline.classify_file raises, stats.failed must be incremented."""
        file_path = self._make_file(tmp_path)
        pipeline = MagicMock()
        pipeline.classify_file.side_effect = RuntimeError("pipeline boom")

        stats = _InboxStats(total=3)

        with patch("para_files.cli.inbox_cmd.move_classified_file") as mock_mover:
            _process_inbox_file(
                file_path,
                pipeline,
                stats,
                idx=1,
                total=3,
                dry_run=False,
                conflict_strategy=ConflictStrategy.RENAME,
                verbose=False,
            )

        assert stats.failed == 1
        assert stats.moved == 0
        assert stats.stayed == 0
        mock_mover.assert_not_called()

    def test_failed_move_increments_failed(self, tmp_path: Path) -> None:
        """When move_classified_file returns success=False, stats.failed must be incremented."""
        file_path = self._make_file(tmp_path)
        pipeline = MagicMock()
        pipeline.classify_file.return_value = self._make_result(ClassificationSource.RULES_ENGINE)
        pipeline.get_target_path.return_value = tmp_path / "3_Resources" / "tests"

        fail_result = MoveResult(
            source=file_path,
            destination=tmp_path / "3_Resources" / "tests" / "test.txt",
            success=False,
            action="error",
            message="Permission denied",
        )

        stats = _InboxStats(total=3)

        with patch("para_files.cli.inbox_cmd.move_classified_file", return_value=fail_result):
            _process_inbox_file(
                file_path,
                pipeline,
                stats,
                idx=1,
                total=3,
                dry_run=False,
                conflict_strategy=ConflictStrategy.RENAME,
                verbose=False,
            )

        assert stats.failed == 1
        assert stats.moved == 0


# ---------------------------------------------------------------------------
# TestPrintInboxSummary — unit tests for _print_inbox_summary
# ---------------------------------------------------------------------------


class TestPrintInboxSummary:
    """Unit tests for _print_inbox_summary function."""

    def test_summary_shows_all_counts(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Summary output must contain total, moved, stayed, and error counts."""
        stats = _InboxStats(
            total=10,
            moved=7,
            stayed=2,
            failed=1,
            by_signal={"rules_engine": 5, "book_detector": 2},
        )
        _print_inbox_summary(stats, dry_run=False)

        captured = capsys.readouterr()
        output = captured.out

        assert "Total processed" in output
        assert "10" in output
        assert "Moved" in output
        assert "7" in output
        assert "Stayed in Inbox" in output
        assert "2" in output
        assert "Errors" in output
        assert "1" in output
        assert "rules_engine" in output
        assert "5" in output

    def test_summary_dry_run_label(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When dry_run=True, summary output must contain 'dry run'."""
        stats = _InboxStats(total=3, moved=2, stayed=1)
        _print_inbox_summary(stats, dry_run=True)

        captured = capsys.readouterr()
        assert "dry run" in captured.out

    def test_summary_no_errors_line_when_zero(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When stats.failed == 0, 'Errors' must NOT appear in summary output."""
        stats = _InboxStats(total=5, moved=4, stayed=1, failed=0)
        _print_inbox_summary(stats, dry_run=False)

        captured = capsys.readouterr()
        assert "Errors" not in captured.out


# ---------------------------------------------------------------------------
# TestInboxCommand — integration tests via CliRunner
# ---------------------------------------------------------------------------


class TestInboxCommand:
    """Integration tests for the inbox CLI command using typer CliRunner."""

    def _make_confident_result(self) -> ClassificationResult:
        """Build a confident ClassificationResult for RULES_ENGINE."""
        return ClassificationResult(
            category="3_Resources/tests",
            confidence=Confidence(value=0.95, source=ClassificationSource.RULES_ENGINE),
        )

    def _make_default_result(self) -> ClassificationResult:
        """Build a DEFAULT ClassificationResult (unclassifiable)."""
        return ClassificationResult(
            category="0_Inbox",
            confidence=Confidence(value=0.0, source=ClassificationSource.DEFAULT),
        )

    def test_inbox_no_files(self, tmp_path: Path) -> None:
        """UX-01: Empty inbox directory must exit 0 and report 'No files found'."""
        runner = CliRunner()

        with (
            patch("para_files.cli.inbox_cmd.load_config_or_exit") as mock_config,
            patch("para_files.cli.inbox_cmd.ClassificationPipeline"),
        ):
            mock_config.return_value = MagicMock(
                inbox_path=tmp_path,
                para_root=tmp_path,
                reference_tree_path=Path("/fake/tree.yaml"),
            )

            result = runner.invoke(app, ["inbox", str(tmp_path)])

        assert result.exit_code == 0
        assert "No files found" in result.output

    def test_inbox_dry_run_does_not_move_files(self, tmp_path: Path) -> None:
        """UX-02: --dry-run must call move_classified_file with dry_run=True."""
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.txt").write_text("content2")

        runner = CliRunner()
        confident_result = self._make_confident_result()
        target_dir = tmp_path / "3_Resources" / "tests"

        success_move = MoveResult(
            source=tmp_path / "file1.txt",
            destination=target_dir / "file1.txt",
            success=True,
            action="would be moved",
            message="Dry run",
        )

        with (
            patch("para_files.cli.inbox_cmd.load_config_or_exit") as mock_config,
            patch("para_files.cli.inbox_cmd.ClassificationPipeline") as mock_pipeline_cls,
            patch(
                "para_files.cli.inbox_cmd.move_classified_file", return_value=success_move
            ) as mock_mover,
        ):
            mock_cfg = MagicMock(
                inbox_path=tmp_path,
                para_root=tmp_path,
                reference_tree_path=Path("/fake/tree.yaml"),
            )
            mock_config.return_value = mock_cfg
            mock_pipeline = MagicMock()
            mock_pipeline.classify_file.return_value = confident_result
            mock_pipeline.get_target_path.return_value = target_dir
            mock_pipeline_cls.return_value = mock_pipeline

            result = runner.invoke(app, ["inbox", str(tmp_path), "--dry-run"])

        assert result.exit_code == 0
        # move_classified_file must have been called with dry_run=True
        for call in mock_mover.call_args_list:
            assert call.kwargs.get("dry_run") is True or call.args[2] is True

    def test_inbox_progress_output_format(self, tmp_path: Path) -> None:
        """UX-03: Progress output must contain [1/1] prefix and destination path."""
        test_file = tmp_path / "report.txt"
        test_file.write_text("content")

        runner = CliRunner()
        confident_result = self._make_confident_result()
        target_dir = tmp_path / "3_Resources" / "tests"
        dest_path = target_dir / "report.txt"

        success_move = MoveResult(
            source=test_file,
            destination=dest_path,
            success=True,
            action="moved",
            message="",
        )

        with (
            patch("para_files.cli.inbox_cmd.load_config_or_exit") as mock_config,
            patch("para_files.cli.inbox_cmd.ClassificationPipeline") as mock_pipeline_cls,
            patch("para_files.cli.inbox_cmd.move_classified_file", return_value=success_move),
        ):
            mock_cfg = MagicMock(
                inbox_path=tmp_path,
                para_root=tmp_path,
                reference_tree_path=Path("/fake/tree.yaml"),
            )
            mock_config.return_value = mock_cfg
            mock_pipeline = MagicMock()
            mock_pipeline.classify_file.return_value = confident_result
            mock_pipeline.get_target_path.return_value = target_dir
            mock_pipeline_cls.return_value = mock_pipeline

            result = runner.invoke(app, ["inbox", str(tmp_path)])

        assert result.exit_code == 0
        assert "[1/1]" in result.output
        assert str(dest_path) in result.output

    def test_inbox_leaves_unclassifiable_files(self, tmp_path: Path) -> None:
        """UX-02: Files classified as DEFAULT stay in inbox; move_classified_file NOT called."""
        test_file = tmp_path / "mystery.txt"
        test_file.write_text("unclassifiable content")

        runner = CliRunner()
        default_result = self._make_default_result()

        with (
            patch("para_files.cli.inbox_cmd.load_config_or_exit") as mock_config,
            patch("para_files.cli.inbox_cmd.ClassificationPipeline") as mock_pipeline_cls,
            patch("para_files.cli.inbox_cmd.move_classified_file") as mock_mover,
        ):
            mock_cfg = MagicMock(
                inbox_path=tmp_path,
                para_root=tmp_path,
                reference_tree_path=Path("/fake/tree.yaml"),
            )
            mock_config.return_value = mock_cfg
            mock_pipeline = MagicMock()
            mock_pipeline.classify_file.return_value = default_result
            mock_pipeline_cls.return_value = mock_pipeline

            result = runner.invoke(app, ["inbox", str(tmp_path)])

        assert result.exit_code == 0
        mock_mover.assert_not_called()
        # Summary should indicate file stayed
        assert (
            "INBOX" in result.output
            or "stayed" in result.output.lower()
            or "Stayed" in result.output
        )

    def test_inbox_summary_by_signal(self, tmp_path: Path) -> None:
        """UX-04: Summary must include by-signal breakdown when files are moved."""
        (tmp_path / "doc1.txt").write_text("content1")
        (tmp_path / "doc2.txt").write_text("content2")

        runner = CliRunner()
        confident_result = self._make_confident_result()
        target_dir = tmp_path / "3_Resources" / "tests"

        def make_success_move(src: Path, *args: object, **kwargs: object) -> MoveResult:
            return MoveResult(
                source=src,
                destination=target_dir / src.name,
                success=True,
                action="moved",
                message="",
            )

        with (
            patch("para_files.cli.inbox_cmd.load_config_or_exit") as mock_config,
            patch("para_files.cli.inbox_cmd.ClassificationPipeline") as mock_pipeline_cls,
            patch("para_files.cli.inbox_cmd.move_classified_file", side_effect=make_success_move),
        ):
            mock_cfg = MagicMock(
                inbox_path=tmp_path,
                para_root=tmp_path,
                reference_tree_path=Path("/fake/tree.yaml"),
            )
            mock_config.return_value = mock_cfg
            mock_pipeline = MagicMock()
            mock_pipeline.classify_file.return_value = confident_result
            mock_pipeline.get_target_path.return_value = target_dir
            mock_pipeline_cls.return_value = mock_pipeline

            result = runner.invoke(app, ["inbox", str(tmp_path)])

        assert result.exit_code == 0
        assert "rules_engine" in result.output
        assert "2" in result.output
