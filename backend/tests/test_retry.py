"""
Tests for retry and circuit breaker functionality.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from app.core.retry import (
    retry,
    async_retry,
    calculate_delay,
    RetryConfig,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    CircuitBreakerOpen,
    get_circuit_breaker,
    _circuit_breakers,
)


class TestRetryConfig:
    """Test RetryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=0.5,
            max_delay=30.0,
        )
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0


class TestCalculateDelay:
    """Test delay calculation."""

    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert calculate_delay(0, config) == 1.0  # 1 * 2^0 = 1
        assert calculate_delay(1, config) == 2.0  # 1 * 2^1 = 2
        assert calculate_delay(2, config) == 4.0  # 1 * 2^2 = 4
        assert calculate_delay(3, config) == 8.0  # 1 * 2^3 = 8

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, jitter=False)

        assert calculate_delay(10, config) == 5.0  # Would be 1024, capped at 5

    def test_jitter_applied(self):
        """Test that jitter adds variation."""
        config = RetryConfig(base_delay=1.0, jitter=True)

        delays = [calculate_delay(1, config) for _ in range(10)]
        # With jitter, delays should vary
        assert len(set(delays)) > 1


class TestCircuitBreaker:
    """Test CircuitBreaker class."""

    def setup_method(self):
        """Clear circuit breakers before each test."""
        _circuit_breakers.clear()

    def test_initial_state_closed(self):
        """Test that circuit starts in closed state."""
        cb = CircuitBreaker("test", CircuitBreakerConfig())
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() == True

    def test_opens_after_failures(self):
        """Test that circuit opens after reaching failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        for i in range(3):
            cb.record_failure(Exception(f"Error {i}"))

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() == False

    def test_success_resets_failure_count(self):
        """Test that success resets failure count."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)

        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))
        cb.record_success()

        assert cb._state.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_half_open_after_timeout(self):
        """Test transition to half-open after recovery timeout."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for testing
        )
        cb = CircuitBreaker("test", config)

        # Trigger open state
        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))
        assert cb._state.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(0.15)

        # Should transition to half-open
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() == True

    def test_half_open_closes_on_success(self):
        """Test that half-open closes after successful calls."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
            success_threshold=2,
        )
        cb = CircuitBreaker("test", config)

        # Get to half-open
        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))
        time.sleep(0.15)
        _ = cb.state  # Triggers state check

        # Record successes
        cb.record_success()
        cb.record_success()

        assert cb.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self):
        """Test that half-open reopens on failure."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,
        )
        cb = CircuitBreaker("test", config)

        # Get to half-open
        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))
        time.sleep(0.15)
        _ = cb.state  # Triggers state check

        # Fail in half-open
        cb.record_failure(Exception("Error in half-open"))

        assert cb._state.state == CircuitState.OPEN

    def test_manual_reset(self):
        """Test manual circuit reset."""
        cb = CircuitBreaker("test", CircuitBreakerConfig(failure_threshold=2))

        cb.record_failure(Exception("Error 1"))
        cb.record_failure(Exception("Error 2"))
        assert cb.state == CircuitState.OPEN

        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._state.failure_count == 0


class TestRetryDecorator:
    """Test the retry decorator."""

    def test_succeeds_first_try(self):
        """Test function succeeds on first try."""
        call_count = 0

        @retry(max_retries=3)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()
        assert result == "success"
        assert call_count == 1

    def test_retries_on_failure(self):
        """Test that function is retried on failure."""
        call_count = 0

        @retry(max_retries=3, base_delay=0.01)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = fail_then_succeed()
        assert result == "success"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        """Test that exception is raised after max retries."""
        call_count = 0

        @retry(max_retries=2, base_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")

        with pytest.raises(Exception, match="Always fails"):
            always_fails()

        assert call_count == 3  # Initial + 2 retries

    def test_only_retries_specified_exceptions(self):
        """Test that only specified exceptions trigger retry."""
        call_count = 0

        @retry(max_retries=3, retryable_exceptions=(ValueError,), base_delay=0.01)
        def raises_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Not retryable")

        with pytest.raises(TypeError):
            raises_type_error()

        assert call_count == 1  # No retries for TypeError

    def test_with_circuit_breaker(self):
        """Test retry with circuit breaker integration."""
        _circuit_breakers.clear()
        call_count = 0

        @retry(
            max_retries=2,
            base_delay=0.01,
            circuit_breaker_name="test_cb",
        )
        def func_with_cb():
            nonlocal call_count
            call_count += 1
            raise Exception("Failure")

        # Should fail and trip circuit breaker eventually
        for _ in range(3):
            try:
                func_with_cb()
            except (Exception, CircuitBreakerOpen):
                pass

        # Circuit should be open now
        cb = get_circuit_breaker("test_cb")
        # After multiple failures, circuit should open
        assert cb._state.failure_count >= 3


class TestGetCircuitBreaker:
    """Test circuit breaker registry."""

    def setup_method(self):
        """Clear circuit breakers before each test."""
        _circuit_breakers.clear()

    def test_creates_new_breaker(self):
        """Test that new breakers are created."""
        cb = get_circuit_breaker("new_breaker")
        assert cb is not None
        assert cb.name == "new_breaker"

    def test_returns_existing_breaker(self):
        """Test that existing breakers are returned."""
        cb1 = get_circuit_breaker("same_breaker")
        cb2 = get_circuit_breaker("same_breaker")
        assert cb1 is cb2

    def test_uses_provided_config(self):
        """Test that provided config is used for new breakers."""
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = get_circuit_breaker("custom_config", config)
        assert cb.config.failure_threshold == 10


@pytest.mark.asyncio
class TestAsyncRetryDecorator:
    """Test the async retry decorator."""

    async def test_async_succeeds_first_try(self):
        """Test async function succeeds on first try."""
        call_count = 0

        @async_retry(max_retries=3)
        async def async_success():
            nonlocal call_count
            call_count += 1
            return "async success"

        result = await async_success()
        assert result == "async success"
        assert call_count == 1

    async def test_async_retries_on_failure(self):
        """Test async function is retried on failure."""
        call_count = 0

        @async_retry(max_retries=3, base_delay=0.01)
        async def async_fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"

        result = await async_fail_then_succeed()
        assert result == "success"
        assert call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
