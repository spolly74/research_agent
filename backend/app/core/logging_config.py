"""
Structured Logging Configuration

This module provides:
- Centralized structlog configuration
- Request ID tracking via context variables
- JSON and console output formatters
- FastAPI middleware for request tracking
- Log aggregation utilities
"""

import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Optional, Any
from collections import deque
from threading import Lock

import structlog
from structlog.types import Processor

# Context variable for request ID tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)

# In-memory log buffer for aggregation endpoint
LOG_BUFFER_SIZE = 1000
_log_buffer: deque = deque(maxlen=LOG_BUFFER_SIZE)
_log_buffer_lock = Lock()


def get_request_id() -> Optional[str]:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    request_id_var.set(request_id)


def get_session_id() -> Optional[str]:
    """Get the current session ID from context."""
    return session_id_var.get()


def set_session_id(session_id: str) -> None:
    """Set the session ID in context."""
    session_id_var.set(session_id)


def generate_request_id() -> str:
    """Generate a new unique request ID."""
    return str(uuid.uuid4())[:8]


def add_request_context(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add request context to log entries."""
    request_id = get_request_id()
    session_id = get_session_id()

    if request_id:
        event_dict["request_id"] = request_id
    if session_id:
        event_dict["session_id"] = session_id

    return event_dict


def add_timestamp(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO timestamp to log entries."""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def buffer_log_entry(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Buffer log entries for the aggregation endpoint."""
    with _log_buffer_lock:
        _log_buffer.append({
            "level": method_name,
            "timestamp": event_dict.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "event": event_dict.get("event", ""),
            "request_id": event_dict.get("request_id"),
            "session_id": event_dict.get("session_id"),
            **{k: v for k, v in event_dict.items()
               if k not in ("level", "timestamp", "event", "request_id", "session_id")}
        })
    return event_dict


def get_buffered_logs(
    limit: int = 100,
    level: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None
) -> list[dict[str, Any]]:
    """
    Get buffered log entries with optional filtering.

    Args:
        limit: Maximum number of entries to return
        level: Filter by log level (debug, info, warning, error)
        request_id: Filter by request ID
        session_id: Filter by session ID

    Returns:
        List of log entries, newest first
    """
    with _log_buffer_lock:
        logs = list(_log_buffer)

    # Apply filters
    if level:
        logs = [l for l in logs if l.get("level") == level]
    if request_id:
        logs = [l for l in logs if l.get("request_id") == request_id]
    if session_id:
        logs = [l for l in logs if l.get("session_id") == session_id]

    # Return newest first, limited
    return list(reversed(logs))[:limit]


def clear_log_buffer() -> int:
    """Clear the log buffer. Returns count of cleared entries."""
    with _log_buffer_lock:
        count = len(_log_buffer)
        _log_buffer.clear()
        return count


def configure_logging(
    json_format: bool = False,
    log_level: str = "INFO",
    enable_buffer: bool = True
) -> None:
    """
    Configure structlog for the application.

    Args:
        json_format: If True, output JSON logs (for production)
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR)
        enable_buffer: If True, buffer logs for aggregation endpoint
    """
    # Shared processors for all configurations
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_request_context,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if enable_buffer:
        shared_processors.append(buffer_log_entry)

    if json_format:
        # Production: JSON output
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: Colored console output
        shared_processors.append(structlog.dev.set_exc_info)
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    shared_processors.append(renderer)

    # Configure structlog
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Set third-party loggers to WARNING to reduce noise
    for logger_name in ["httpx", "httpcore", "urllib3", "asyncio"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


class RequestContextMiddleware:
    """
    FastAPI middleware to add request context for logging.

    Adds request ID and tracks request timing.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate and set request ID
        request_id = generate_request_id()
        set_request_id(request_id)

        # Get logger and log request start
        logger = structlog.get_logger("request")
        start_time = datetime.utcnow()

        # Extract request info
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        logger.info(
            "Request started",
            method=method,
            path=path,
        )

        # Track response status
        response_status = None

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            logger.error(
                "Request failed",
                method=method,
                path=path,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            # Log request completion
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                "Request completed",
                method=method,
                path=path,
                status=response_status,
                duration_ms=round(duration_ms, 2),
            )

            # Clear context
            request_id_var.set(None)
            session_id_var.set(None)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    """
    Get a structlog logger instance.

    This is the preferred way to get a logger in the application.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Convenience function for setting session context
def with_session_context(session_id: str):
    """
    Context manager for setting session ID in logs.

    Usage:
        with with_session_context("session-123"):
            logger.info("Processing session")
    """
    class SessionContext:
        def __enter__(self):
            set_session_id(session_id)
            return self

        def __exit__(self, *args):
            session_id_var.set(None)

    return SessionContext()
