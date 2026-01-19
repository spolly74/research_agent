"""
Resilient LLM invocation wrapper with retry and circuit breaker support.

Provides reliable LLM calls with:
- Automatic retry with exponential backoff
- Circuit breaker for failing endpoints
- Fallback to alternative providers
- Error categorization and recovery
"""

import structlog
from typing import Any, List, Optional, Union
from langchain_core.messages import BaseMessage
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.retry import (
    retry,
    get_circuit_breaker,
    CircuitBreakerOpen,
    CircuitBreakerConfig,
)
from app.core.llm_manager import get_llm, TaskType, Provider

logger = structlog.get_logger(__name__)


# Configure circuit breakers for different providers
OLLAMA_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=60.0,
    half_open_max_calls=1,
    success_threshold=2,
)

CLAUDE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=120.0,
    half_open_max_calls=1,
    success_threshold=2,
)


class LLMInvocationError(Exception):
    """Base exception for LLM invocation errors."""
    pass


class RetryableError(LLMInvocationError):
    """Error that should trigger a retry."""
    pass


class NonRetryableError(LLMInvocationError):
    """Error that should not be retried."""
    pass


def categorize_error(error: Exception) -> type:
    """
    Categorize an error as retryable or not.

    Args:
        error: The exception to categorize

    Returns:
        Either RetryableError or NonRetryableError class
    """
    error_str = str(error).lower()

    # Non-retryable errors
    non_retryable_patterns = [
        "invalid api key",
        "authentication failed",
        "unauthorized",
        "model not found",
        "invalid model",
        "context length exceeded",
        "content policy",
        "rate limit",  # Special handling needed
    ]

    for pattern in non_retryable_patterns:
        if pattern in error_str:
            return NonRetryableError

    # Retryable errors
    retryable_patterns = [
        "timeout",
        "connection",
        "network",
        "server error",
        "503",
        "502",
        "500",
        "overloaded",
        "temporarily unavailable",
    ]

    for pattern in retryable_patterns:
        if pattern in error_str:
            return RetryableError

    # Default to retryable for unknown errors
    return RetryableError


@retry(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    retryable_exceptions=(RetryableError, ConnectionError, TimeoutError),
    circuit_breaker_name="ollama",
)
def invoke_ollama_with_retry(
    llm: BaseChatModel,
    messages: List[BaseMessage],
) -> BaseMessage:
    """
    Invoke Ollama LLM with retry logic.

    Args:
        llm: The Ollama LLM instance
        messages: Messages to send

    Returns:
        The response message
    """
    try:
        return llm.invoke(messages)
    except Exception as e:
        error_type = categorize_error(e)
        if error_type == NonRetryableError:
            raise NonRetryableError(str(e)) from e
        raise RetryableError(str(e)) from e


@retry(
    max_retries=3,
    base_delay=2.0,
    max_delay=60.0,
    retryable_exceptions=(RetryableError, ConnectionError, TimeoutError),
    circuit_breaker_name="claude",
)
def invoke_claude_with_retry(
    llm: BaseChatModel,
    messages: List[BaseMessage],
) -> BaseMessage:
    """
    Invoke Claude LLM with retry logic.

    Args:
        llm: The Claude LLM instance
        messages: Messages to send

    Returns:
        The response message
    """
    try:
        return llm.invoke(messages)
    except Exception as e:
        error_type = categorize_error(e)
        if error_type == NonRetryableError:
            raise NonRetryableError(str(e)) from e
        raise RetryableError(str(e)) from e


def invoke_with_fallback(
    messages: List[BaseMessage],
    task_type: TaskType = TaskType.GENERAL,
    primary_provider: Optional[Provider] = None,
) -> BaseMessage:
    """
    Invoke an LLM with automatic fallback between providers.

    Tries the primary provider first, falls back to the other on failure.

    Args:
        messages: Messages to send
        task_type: The task type for routing
        primary_provider: Preferred provider (auto-selects if None)

    Returns:
        The response message
    """
    providers = [Provider.OLLAMA, Provider.CLAUDE]
    if primary_provider:
        providers = [primary_provider] + [p for p in providers if p != primary_provider]

    last_error = None

    for provider in providers:
        try:
            llm = get_llm(task_type=task_type, force_provider=provider)

            if provider == Provider.OLLAMA:
                result = invoke_ollama_with_retry(llm, messages)
            else:
                result = invoke_claude_with_retry(llm, messages)

            logger.info(
                "LLM invocation successful",
                provider=provider.value,
                task_type=task_type.value,
            )
            return result

        except CircuitBreakerOpen as e:
            logger.warning(
                "Circuit breaker open, skipping provider",
                provider=provider.value,
            )
            last_error = e
            continue

        except NonRetryableError as e:
            logger.error(
                "Non-retryable error from provider",
                provider=provider.value,
                error=str(e),
            )
            last_error = e
            continue

        except Exception as e:
            logger.error(
                "Provider failed after retries",
                provider=provider.value,
                error=str(e),
            )
            last_error = e
            continue

    # All providers failed
    raise LLMInvocationError(f"All providers failed. Last error: {last_error}")


class ResilientLLM:
    """
    A wrapper around LLMs that provides resilient invocation.

    Can be used as a drop-in replacement for direct LLM usage.
    """

    def __init__(
        self,
        task_type: TaskType = TaskType.GENERAL,
        primary_provider: Optional[Provider] = None,
    ):
        self.task_type = task_type
        self.primary_provider = primary_provider
        self._llm = get_llm(task_type=task_type, force_provider=primary_provider)

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """Invoke the LLM with resilience features."""
        return invoke_with_fallback(
            messages,
            task_type=self.task_type,
            primary_provider=self.primary_provider,
        )

    def bind_tools(self, tools: List[Any]) -> "ResilientLLMWithTools":
        """Bind tools to the LLM."""
        return ResilientLLMWithTools(
            task_type=self.task_type,
            primary_provider=self.primary_provider,
            tools=tools,
        )


class ResilientLLMWithTools:
    """
    Resilient LLM wrapper with tool support.
    """

    def __init__(
        self,
        task_type: TaskType,
        primary_provider: Optional[Provider],
        tools: List[Any],
    ):
        self.task_type = task_type
        self.primary_provider = primary_provider
        self.tools = tools

    def invoke(self, messages: List[BaseMessage]) -> BaseMessage:
        """Invoke the LLM with tools and resilience features."""
        # Get LLM and bind tools
        llm = get_llm(task_type=self.task_type, force_provider=self.primary_provider)
        llm_with_tools = llm.bind_tools(self.tools)

        try:
            return llm_with_tools.invoke(messages)
        except Exception as e:
            # If primary fails, try fallback provider
            fallback_provider = (
                Provider.CLAUDE
                if self.primary_provider == Provider.OLLAMA
                else Provider.OLLAMA
            )

            try:
                logger.warning(
                    "Primary provider failed, trying fallback",
                    primary=self.primary_provider,
                    fallback=fallback_provider,
                    error=str(e),
                )
                llm = get_llm(task_type=self.task_type, force_provider=fallback_provider)
                llm_with_tools = llm.bind_tools(self.tools)
                return llm_with_tools.invoke(messages)
            except Exception as fallback_error:
                logger.error(
                    "Both providers failed",
                    primary_error=str(e),
                    fallback_error=str(fallback_error),
                )
                raise LLMInvocationError(
                    f"All providers failed. Primary: {e}, Fallback: {fallback_error}"
                )


def get_resilient_llm(
    task_type: TaskType = TaskType.GENERAL,
    primary_provider: Optional[Provider] = None,
) -> ResilientLLM:
    """
    Get a resilient LLM instance.

    Args:
        task_type: The task type for routing
        primary_provider: Preferred provider

    Returns:
        A ResilientLLM instance
    """
    return ResilientLLM(task_type=task_type, primary_provider=primary_provider)


# Initialize circuit breakers on module load
get_circuit_breaker("ollama", OLLAMA_CIRCUIT_CONFIG)
get_circuit_breaker("claude", CLAUDE_CIRCUIT_CONFIG)
