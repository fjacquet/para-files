"""Circuit breaker for the model fallback: stop calling after N failures in a row."""

from __future__ import annotations

import threading

from loguru import logger


class CircuitBreaker:
    """Opens after `threshold` consecutive failures and stays open for the rest of the run.

    Consecutive failures across all workers; any success resets the count.
    """

    def __init__(self, threshold: int = 3) -> None:
        """Start closed, with no failures counted."""
        self._threshold = threshold
        self._failures = 0
        self._open = False
        self._lock = threading.Lock()

    @property
    def is_open(self) -> bool:
        """True once the breaker has tripped."""
        return self._open

    def record_failure(self) -> None:
        """Count one failure; open the breaker when the count reaches the threshold."""
        with self._lock:
            self._failures += 1
            if self._failures >= self._threshold and not self._open:
                logger.warning("model fallback off for this run after {} failures", self._failures)
                self._open = True

    def record_success(self) -> None:
        """Reset the failure count; an open breaker stays open."""
        with self._lock:
            self._failures = 0
