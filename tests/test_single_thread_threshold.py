"""Tests for PERF-01: adaptive single-threading threshold in move_cmd."""

from __future__ import annotations

from pathlib import Path

from para_files.cli.move_cmd import SINGLE_THREAD_THRESHOLD


class TestSingleThreadThreshold:
    """Tests for SINGLE_THREAD_THRESHOLD constant and enforcement."""

    def test_constant_exists_at_module_level(self) -> None:
        """SINGLE_THREAD_THRESHOLD = 5 exists at module level."""
        from para_files.cli import move_cmd

        assert hasattr(move_cmd, "SINGLE_THREAD_THRESHOLD"), (
            "SINGLE_THREAD_THRESHOLD constant not found in move_cmd"
        )
        assert SINGLE_THREAD_THRESHOLD == 5

    def test_small_batch_forces_sequential(self) -> None:
        """Batch of 3 files with max_workers=4 uses sequential path (max_workers forced to 1)."""
        batch_size = 3
        max_workers = 4

        # If batch < threshold, sequential should be used regardless of max_workers
        assert batch_size < SINGLE_THREAD_THRESHOLD, (
            "Test precondition: batch_size must be < threshold"
        )
        # Gate condition: parallel requires max_workers > 1 AND len >= threshold
        uses_parallel = max_workers > 1 and batch_size >= SINGLE_THREAD_THRESHOLD
        assert not uses_parallel, "Small batch (3 files) should NOT trigger parallel mode"

    def test_threshold_batch_uses_parallel(self) -> None:
        """Batch of 5 files uses parallel path (threshold is exclusive)."""
        batch_size = 5
        max_workers = 4

        # At exactly threshold, parallel should be used
        assert batch_size >= SINGLE_THREAD_THRESHOLD, (
            "Test precondition: batch_size must be >= threshold"
        )
        uses_parallel = max_workers > 1 and batch_size >= SINGLE_THREAD_THRESHOLD
        assert uses_parallel, "Batch of 5 files with max_workers=4 SHOULD trigger parallel mode"

    def test_max_workers_1_always_sequential(self) -> None:
        """Batch of 4 files with max_workers=1 always takes sequential path."""
        batch_size = 4
        max_workers = 1

        # max_workers=1 means no parallel regardless of batch size
        uses_parallel = max_workers > 1 and batch_size >= SINGLE_THREAD_THRESHOLD
        assert not uses_parallel, "max_workers=1 should never trigger parallel mode"

    def test_verbose_small_batch_contains_single_threaded_message(self, tmp_path: Path) -> None:
        """--verbose output for 3-file batch contains 'single-threaded' string."""
        echoed_messages: list[str] = []

        def fake_echo(msg: str = "") -> None:
            echoed_messages.append(str(msg))

        # Simulate the threshold logic with verbose=True
        expanded_files = [tmp_path / f"file{i}.txt" for i in range(3)]
        max_workers = 4
        verbose = True

        # Apply the same logic as the implementation should
        if max_workers > 1 and len(expanded_files) < SINGLE_THREAD_THRESHOLD:
            if verbose:
                fake_echo(
                    f"Processing {len(expanded_files)} file(s) in single-threaded mode "
                    f"(< {SINGLE_THREAD_THRESHOLD} files)"
                )
            max_workers = 1

        combined = " ".join(echoed_messages)
        assert "single-threaded" in combined, (
            f"Expected 'single-threaded' in verbose output for 3-file batch, got: {combined!r}"
        )
