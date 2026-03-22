"""Ollama circuit breaker and health check utilities.

Provides:
- OllamaCircuitBreaker: Trip-after-N-failures breaker to skip Ollama calls
  when the server is repeatedly unreachable.
- check_ollama_health: Lightweight HTTP probe to /api/tags to determine
  whether the Ollama server is reachable before starting the pipeline.
"""

from __future__ import annotations

import httpx
from loguru import logger


class OllamaCircuitBreaker:
    """Circuit breaker that trips after N consecutive Ollama failures.

    Once open (tripped), callers should skip Ollama-dependent operations
    rather than accumulating more timeout penalties.

    Usage::

        cb = OllamaCircuitBreaker(threshold=3)

        if cb.is_open:
            # skip Ollama call
        else:
            try:
                result = call_ollama(...)
                cb.record_success()
            except (ConnectionError, TimeoutError, OSError):
                cb.record_failure()

    Attributes:
        threshold: Number of consecutive failures before the breaker opens.
    """

    def __init__(self, threshold: int = 3) -> None:
        """Initialize breaker in closed (operational) state.

        Args:
            threshold: Consecutive failure count needed to open the breaker.
        """
        self._threshold = threshold
        self._consecutive_failures = 0
        self._open = False

    @property
    def is_open(self) -> bool:
        """Return True when the circuit breaker has tripped."""
        return self._open

    def record_failure(self) -> None:
        """Record one failure; open the breaker if threshold is reached."""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._threshold:
            if not self._open:
                logger.warning(
                    "Ollama circuit breaker tripped after {} consecutive failures",
                    self._consecutive_failures,
                )
            self._open = True

    def record_success(self) -> None:
        """Reset the consecutive failure counter (does not close the breaker).

        The breaker remains open once tripped. Call reset() to fully close it.
        """
        self._consecutive_failures = 0

    def reset(self) -> None:
        """Fully close the breaker and clear the failure counter."""
        self._consecutive_failures = 0
        self._open = False


def check_ollama_health(
    api_base: str = "http://localhost:11434",
    timeout: float = 3.0,
) -> bool:
    """Probe the Ollama API to check whether it is reachable.

    Sends an HTTP GET to ``{api_base}/api/tags`` with a short timeout.
    Uses httpx (already a project dependency via litellm).

    Args:
        api_base: Ollama server base URL.
        timeout:  Connection + read timeout in seconds.

    Returns:
        True if the server responded (any HTTP status is accepted as
        "reachable"), False on any network or OS error.
    """
    url = f"{api_base.rstrip('/')}/api/tags"
    try:
        httpx.get(url, timeout=timeout)
    except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError, OSError):
        logger.debug("Ollama health check failed for {}", url)
        return False
    else:
        return True
