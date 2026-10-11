"""Ctrl+C handling for parallel CLI loops (Stage 0 final review C1)."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from para_files.cli.shared import cancel_pending_on_interrupt


def test_interrupt_drops_queued_tasks() -> None:
    """After Ctrl+C only in-flight tasks finish; queued ones never start."""
    started = 0
    lock = threading.Lock()

    def work(_: int) -> None:
        nonlocal started
        with lock:
            started += 1
        time.sleep(0.05)

    def run_with_interrupt() -> None:
        with (
            ThreadPoolExecutor(max_workers=4) as executor,
            cancel_pending_on_interrupt(executor),
        ):
            futures = [executor.submit(work, i) for i in range(40)]
            for _ in as_completed(futures):
                raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_with_interrupt()

    assert started <= 8
