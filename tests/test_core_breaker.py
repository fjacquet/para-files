"""The model fallback's circuit breaker."""

from __future__ import annotations

import threading

from para_files.core.breaker import CircuitBreaker


def test_opens_after_threshold_failures_in_a_row():
    breaker = CircuitBreaker(threshold=2)
    breaker.record_failure()
    assert not breaker.is_open
    breaker.record_failure()
    assert breaker.is_open


def test_a_success_resets_the_count():
    breaker = CircuitBreaker(threshold=2)
    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()
    assert not breaker.is_open


def test_an_open_breaker_stays_open():
    breaker = CircuitBreaker(threshold=1)
    breaker.record_failure()
    breaker.record_success()
    assert breaker.is_open


def test_concurrent_failures_are_all_counted():
    breaker = CircuitBreaker(threshold=8000)

    def hammer() -> None:
        for _ in range(1000):
            breaker.record_failure()

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert breaker.is_open
    assert breaker._failures == 8000
