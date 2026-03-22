"""Tests for OllamaCircuitBreaker and check_ollama_health."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from para_files.circuit_breaker import OllamaCircuitBreaker, check_ollama_health
from para_files.encoders.ollama_encoder import OllamaEncoder


# ---------------------------------------------------------------------------
# OllamaCircuitBreaker tests
# ---------------------------------------------------------------------------


class TestOllamaCircuitBreaker:
    """Tests for OllamaCircuitBreaker."""

    def test_starts_closed(self) -> None:
        """Circuit breaker starts in closed (operational) state."""
        cb = OllamaCircuitBreaker()
        assert cb.is_open is False

    def test_trips_after_threshold_failures(self) -> None:
        """Circuit breaker opens after threshold consecutive failures (default 3)."""
        cb = OllamaCircuitBreaker(threshold=3)
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_custom_threshold(self) -> None:
        """Circuit breaker respects custom threshold."""
        cb = OllamaCircuitBreaker(threshold=2)
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_reset_closes_breaker(self) -> None:
        """reset() returns breaker to closed state."""
        cb = OllamaCircuitBreaker(threshold=1)
        cb.record_failure()
        assert cb.is_open is True
        cb.reset()
        assert cb.is_open is False

    def test_reset_clears_failure_count(self) -> None:
        """reset() clears consecutive failure count so threshold requires fresh failures."""
        cb = OllamaCircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.reset()
        # After reset, needs threshold failures again
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_record_success_resets_failure_count(self) -> None:
        """record_success() resets consecutive failure count to 0."""
        cb = OllamaCircuitBreaker(threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_success()
        # After success, needs threshold failures again
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open is False
        cb.record_failure()
        assert cb.is_open is True

    def test_record_success_does_not_close_open_breaker(self) -> None:
        """record_success() alone does not close an already-open breaker."""
        cb = OllamaCircuitBreaker(threshold=1)
        cb.record_failure()
        assert cb.is_open is True
        cb.record_success()
        # record_success only resets count, not the open flag — use reset() for that
        assert cb.is_open is True


# ---------------------------------------------------------------------------
# check_ollama_health tests
# ---------------------------------------------------------------------------


class TestCheckOllamaHealth:
    """Tests for check_ollama_health."""

    def test_returns_true_when_server_reachable(self) -> None:
        """Returns True when HTTP GET to /api/tags succeeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            result = check_ollama_health("http://localhost:11434", timeout=3.0)

        assert result is True

    def test_returns_false_on_connect_error(self) -> None:
        """Returns False when connection is refused."""
        import httpx

        with patch("httpx.get", side_effect=httpx.ConnectError("Connection refused")):
            result = check_ollama_health("http://localhost:11434", timeout=3.0)

        assert result is False

    def test_returns_false_on_os_error(self) -> None:
        """Returns False on OS-level errors (e.g., host not found)."""
        with patch("httpx.get", side_effect=OSError("Network unreachable")):
            result = check_ollama_health("http://localhost:11434", timeout=3.0)

        assert result is False

    def test_returns_false_on_timeout(self) -> None:
        """Returns False when the request times out."""
        import httpx

        with patch("httpx.get", side_effect=httpx.TimeoutException("timed out")):
            result = check_ollama_health("http://localhost:11434", timeout=1.0)

        assert result is False

    def test_uses_correct_url(self) -> None:
        """Calls /api/tags endpoint on the provided api_base."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response) as mock_get:
            check_ollama_health("http://myhost:12345", timeout=3.0)

        called_url = mock_get.call_args[0][0]
        assert "myhost:12345" in called_url
        assert "/api/tags" in called_url


# ---------------------------------------------------------------------------
# OllamaEncoder._encode_single connection-error short-circuit tests
# ---------------------------------------------------------------------------


class TestOllamaEncoderConnectionErrorShortCircuit:
    """Tests that _encode_single short-circuits on connection errors."""

    def test_connection_error_returns_zero_vector_immediately(self) -> None:
        """On ConnectionError, _encode_single returns zero vector without retrying."""
        encoder = OllamaEncoder()

        call_count = 0

        def raise_connection_error(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            msg = "Connection refused"
            raise ConnectionError(msg)

        encoder._encode_texts = raise_connection_error  # type: ignore[method-assign]
        result = encoder._encode_single("some text content")

        assert result == [0.0] * 768
        # Must NOT retry — only 1 call
        assert call_count == 1

    def test_os_error_returns_zero_vector_immediately(self) -> None:
        """On OSError, _encode_single returns zero vector without retrying."""
        encoder = OllamaEncoder()

        call_count = 0

        def raise_os_error(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            msg = "Network unreachable"
            raise OSError(msg)

        encoder._encode_texts = raise_os_error  # type: ignore[method-assign]
        result = encoder._encode_single("some text content")

        assert result == [0.0] * 768
        assert call_count == 1

    def test_timeout_error_returns_zero_vector_immediately(self) -> None:
        """On TimeoutError, _encode_single returns zero vector without retrying."""
        encoder = OllamaEncoder()

        call_count = 0

        def raise_timeout_error(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            msg = "Request timed out"
            raise TimeoutError(msg)

        encoder._encode_texts = raise_timeout_error  # type: ignore[method-assign]
        result = encoder._encode_single("some text content")

        assert result == [0.0] * 768
        assert call_count == 1

    def test_value_error_retries_with_shorter_candidates(self) -> None:
        """On ValueError (payload error), _encode_single retries with shorter text."""
        encoder = OllamaEncoder()

        call_count = 0

        def raise_value_error_then_succeed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "Payload too large"
                raise ValueError(msg)
            return [[0.1] * 768]

        encoder._encode_texts = raise_value_error_then_succeed  # type: ignore[method-assign]
        result = encoder._encode_single("some text content")

        assert result == [0.1] * 768
        # Should have retried (at least 2 calls)
        assert call_count >= 2

    def test_runtime_error_retries_with_shorter_candidates(self) -> None:
        """On RuntimeError, _encode_single retries with shorter text."""
        encoder = OllamaEncoder()

        call_count = 0

        def raise_runtime_error_then_succeed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                msg = "Model error"
                raise RuntimeError(msg)
            return [[0.2] * 768]

        encoder._encode_texts = raise_runtime_error_then_succeed  # type: ignore[method-assign]
        result = encoder._encode_single("some text content")

        assert result == [0.2] * 768
        assert call_count >= 2


# ---------------------------------------------------------------------------
# LLMConfig api_key field tests
# ---------------------------------------------------------------------------


class TestLLMConfigApiKey:
    """Tests for LLMConfig.api_key field."""

    def test_api_key_defaults_to_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """api_key field defaults to None when env var is absent."""
        from para_files.config import LLMConfig

        monkeypatch.delenv("PARA_FILES_LLM_API_KEY", raising=False)
        # Bypass .env file to test pure default value
        config = LLMConfig(_env_file=None)  # type: ignore[call-arg]
        assert config.api_key is None

    def test_api_key_can_be_set_directly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """api_key field accepts a string value."""
        from para_files.config import LLMConfig

        monkeypatch.delenv("PARA_FILES_LLM_API_KEY", raising=False)
        config = LLMConfig(api_key="sk-test-key-123", _env_file=None)  # type: ignore[call-arg]
        assert config.api_key == "sk-test-key-123"

    def test_api_key_from_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """api_key is loaded from PARA_FILES_LLM_API_KEY environment variable."""
        from para_files.config import LLMConfig

        monkeypatch.setenv("PARA_FILES_LLM_API_KEY", "env-key-abc")
        config = LLMConfig(_env_file=None)  # type: ignore[call-arg]
        assert config.api_key == "env-key-abc"
