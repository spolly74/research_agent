"""
Retry and circuit breaker utilities for resilient LLM calls.

Provides decorators for:
- Exponential backoff retry logic
- Circuit breaker pattern to prevent cascade failures
- Error tracking and recovery
"""

import asyncio
import functools
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Optional, Set, Type, TypeVar, Union
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # failures before opening
    recovery_timeout: float = 30.0  # seconds before trying half-open
    half_open_max_calls: int = 1  # calls allowed in half-open state
    success_threshold: int = 2  # successes needed to close


@dataclass
class CircuitBreakerState:
    """State tracking for a circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting external calls.

    Opens when failure threshold is reached, preventing further calls
    until the recovery timeout expires.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitBreakerState()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, checking for recovery timeout."""
        if self._state.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state.state = CircuitState.HALF_OPEN
                self._state.half_open_calls = 0
                self._state.success_count = 0
                logger.info("Circuit breaker entering half-open state", name=self.name)

        return self._state.state

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try half-open."""
        if self._state.last_failure_time is None:
            return True

        elapsed = datetime.now(timezone.utc) - self._state.last_failure_time
        return elapsed.total_seconds() >= self.config.recovery_timeout

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state  # This updates state if needed

        if state == CircuitState.CLOSED:
            return True

        if state == CircuitState.OPEN:
            return False

        # Half-open: allow limited calls
        if self._state.half_open_calls < self.config.half_open_max_calls:
            self._state.half_open_calls += 1
            return True

        return False

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state.state == CircuitState.HALF_OPEN:
            self._state.success_count += 1
            if self._state.success_count >= self.config.success_threshold:
                self._state.state = CircuitState.CLOSED
                self._state.failure_count = 0
                logger.info("Circuit breaker closed after recovery", name=self.name)
        else:
            # Reset failure count on success in closed state
            self._state.failure_count = 0

    def record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        self._state.failure_count += 1
        self._state.last_failure_time = datetime.now(timezone.utc)

        if self._state.state == CircuitState.HALF_OPEN:
            # Failure in half-open returns to open
            self._state.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker reopened after half-open failure",
                name=self.name,
                error=str(error),
            )
        elif self._state.failure_count >= self.config.failure_threshold:
            self._state.state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker opened due to failures",
                name=self.name,
                failure_count=self._state.failure_count,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitBreakerState()
        logger.info("Circuit breaker manually reset", name=self.name)


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """
    Calculate delay for a retry attempt using exponential backoff.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds
    """
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)

    if config.jitter:
        import random
        delay = delay * (0.5 + random.random())

    return delay


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    circuit_breaker_name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for synchronous functions with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exception types to retry
        circuit_breaker_name: Optional circuit breaker to use

    Returns:
        Decorated function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            circuit_breaker = None
            if circuit_breaker_name:
                circuit_breaker = get_circuit_breaker(circuit_breaker_name)
                if not circuit_breaker.can_execute():
                    raise CircuitBreakerOpen(f"Circuit breaker '{circuit_breaker_name}' is open")

            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result

                except config.retryable_exceptions as e:
                    last_exception = e

                    if circuit_breaker:
                        circuit_breaker.record_failure(e)

                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            "Retry attempt failed",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=config.max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "All retry attempts failed",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e),
                        )

            raise last_exception

        return wrapper
    return decorator


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    circuit_breaker_name: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for async functions with retry logic.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        retryable_exceptions: Tuple of exception types to retry
        circuit_breaker_name: Optional circuit breaker to use

    Returns:
        Decorated async function
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        retryable_exceptions=retryable_exceptions,
    )

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            circuit_breaker = None
            if circuit_breaker_name:
                circuit_breaker = get_circuit_breaker(circuit_breaker_name)
                if not circuit_breaker.can_execute():
                    raise CircuitBreakerOpen(f"Circuit breaker '{circuit_breaker_name}' is open")

            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    return result

                except config.retryable_exceptions as e:
                    last_exception = e

                    if circuit_breaker:
                        circuit_breaker.record_failure(e)

                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            "Async retry attempt failed",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=config.max_retries,
                            delay=delay,
                            error=str(e),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All async retry attempts failed",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e),
                        )

            raise last_exception

        return wrapper
    return decorator


# Predefined retry configurations for common use cases
LLM_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
)

TOOL_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    base_delay=0.5,
    max_delay=10.0,
    exponential_base=2.0,
)

API_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=0.5,
    max_delay=15.0,
    exponential_base=2.0,
)
