"""
Log Aggregation API endpoints.

Provides endpoints for:
- Retrieving buffered logs
- Filtering logs by level, request ID, session ID
- Clearing log buffer
"""

from fastapi import APIRouter, Query
from typing import Optional, Any

from app.core.logging_config import (
    get_buffered_logs,
    clear_log_buffer,
    LOG_BUFFER_SIZE,
    get_logger
)

router = APIRouter()
logger = get_logger(__name__)


@router.get("")
def list_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Max logs to return"),
    level: Optional[str] = Query(default=None, description="Filter by level: debug, info, warning, error"),
    request_id: Optional[str] = Query(default=None, description="Filter by request ID"),
    session_id: Optional[str] = Query(default=None, description="Filter by session ID"),
) -> dict[str, Any]:
    """
    Get buffered log entries with optional filtering.

    Returns logs in reverse chronological order (newest first).
    """
    # Validate level if provided
    valid_levels = {"debug", "info", "warning", "error"}
    if level and level.lower() not in valid_levels:
        return {
            "error": f"Invalid level '{level}'. Valid levels: {', '.join(valid_levels)}",
            "logs": [],
            "count": 0
        }

    logs = get_buffered_logs(
        limit=limit,
        level=level.lower() if level else None,
        request_id=request_id,
        session_id=session_id
    )

    return {
        "logs": logs,
        "count": len(logs),
        "buffer_size": LOG_BUFFER_SIZE,
        "filters": {
            "limit": limit,
            "level": level,
            "request_id": request_id,
            "session_id": session_id
        }
    }


@router.get("/levels")
def list_log_levels() -> dict[str, Any]:
    """
    Get available log levels and their descriptions.
    """
    return {
        "levels": {
            "debug": "Detailed debugging information",
            "info": "General operational information",
            "warning": "Warning messages for potentially problematic situations",
            "error": "Error messages for failures and exceptions"
        },
        "default": "info"
    }


@router.get("/stats")
def get_log_stats() -> dict[str, Any]:
    """
    Get statistics about buffered logs.
    """
    all_logs = get_buffered_logs(limit=LOG_BUFFER_SIZE)

    # Count by level
    level_counts = {}
    for log in all_logs:
        level = log.get("level", "unknown")
        level_counts[level] = level_counts.get(level, 0) + 1

    # Get unique request and session IDs
    request_ids = set(log.get("request_id") for log in all_logs if log.get("request_id"))
    session_ids = set(log.get("session_id") for log in all_logs if log.get("session_id"))

    return {
        "total_buffered": len(all_logs),
        "buffer_size": LOG_BUFFER_SIZE,
        "buffer_usage_percent": round(len(all_logs) / LOG_BUFFER_SIZE * 100, 1),
        "level_counts": level_counts,
        "unique_request_ids": len(request_ids),
        "unique_session_ids": len(session_ids)
    }


@router.delete("")
def clear_logs() -> dict[str, Any]:
    """
    Clear the log buffer.

    Note: This only clears the in-memory buffer, not any persistent logs.
    """
    logger.info("Log buffer cleared via API")
    count = clear_log_buffer()

    return {
        "success": True,
        "cleared_count": count,
        "message": f"Cleared {count} log entries from buffer"
    }


@router.get("/request/{request_id}")
def get_logs_by_request(
    request_id: str,
    limit: int = Query(default=100, ge=1, le=1000)
) -> dict[str, Any]:
    """
    Get all logs for a specific request ID.
    """
    logs = get_buffered_logs(limit=limit, request_id=request_id)

    return {
        "request_id": request_id,
        "logs": logs,
        "count": len(logs)
    }


@router.get("/session/{session_id}")
def get_logs_by_session(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000)
) -> dict[str, Any]:
    """
    Get all logs for a specific session ID.
    """
    logs = get_buffered_logs(limit=limit, session_id=session_id)

    return {
        "session_id": session_id,
        "logs": logs,
        "count": len(logs)
    }
