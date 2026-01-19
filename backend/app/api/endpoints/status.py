"""
Status API Endpoints

Provides REST endpoints for:
- Polling session status (fallback to WebSocket)
- Listing active sessions
- Session history
"""

from fastapi import APIRouter, HTTPException
from typing import Any, Optional
import structlog

from app.core.execution_tracker import get_execution_tracker, ExecutionPhase

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/{session_id}")
def get_session_status(session_id: str) -> dict[str, Any]:
    """
    Get the current status of a research session.

    This is a polling alternative to the WebSocket endpoint.

    Args:
        session_id: The session identifier

    Returns:
        Current execution status
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    return {
        "success": True,
        "session_id": session_id,
        "status": status.to_dict()
    }


@router.get("/")
def list_sessions(
    active_only: bool = True,
    limit: int = 50
) -> dict[str, Any]:
    """
    List all tracked sessions.

    Args:
        active_only: Only return active (non-completed) sessions
        limit: Maximum number of sessions to return

    Returns:
        List of sessions with summary info
    """
    tracker = get_execution_tracker()
    all_sessions = tracker.get_all_sessions()

    sessions = []
    for session_id, status in all_sessions.items():
        if active_only and status.current_phase in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR]:
            continue

        sessions.append({
            "session_id": session_id,
            "phase": status.current_phase.value,
            "progress": status.progress,
            "active_agent": status.active_agent,
            "started_at": status.started_at.isoformat(),
            "updated_at": status.updated_at.isoformat(),
            "has_error": status.error is not None
        })

        if len(sessions) >= limit:
            break

    return {
        "success": True,
        "count": len(sessions),
        "total": len(all_sessions),
        "sessions": sessions
    }


@router.get("/{session_id}/plan")
def get_session_plan(session_id: str) -> dict[str, Any]:
    """
    Get the research plan for a session.

    Args:
        session_id: The session identifier

    Returns:
        The orchestrator's plan
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not status.plan:
        raise HTTPException(status_code=404, detail="Plan not yet created for this session")

    return {
        "success": True,
        "session_id": session_id,
        "plan": status.plan
    }


@router.get("/{session_id}/agents")
def get_session_agents(session_id: str) -> dict[str, Any]:
    """
    Get the agent execution history for a session.

    Args:
        session_id: The session identifier

    Returns:
        List of agent executions
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    agents = []
    for agent in status.agent_history:
        agents.append({
            "agent": agent.agent_name,
            "started_at": agent.started_at.isoformat(),
            "completed_at": agent.completed_at.isoformat() if agent.completed_at else None,
            "status": agent.status,
            "tools_used": [
                {
                    "tool": t.tool_name,
                    "success": t.success,
                    "started_at": t.started_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in agent.tools_used
            ],
            "result_summary": agent.result_summary
        })

    # Add current agent if active
    if status.current_agent_execution:
        current = status.current_agent_execution
        agents.append({
            "agent": current.agent_name,
            "started_at": current.started_at.isoformat(),
            "completed_at": None,
            "status": "running",
            "progress": current.progress,
            "tools_used": [
                {
                    "tool": t.tool_name,
                    "success": t.success,
                    "started_at": t.started_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in current.tools_used
            ]
        })

    return {
        "success": True,
        "session_id": session_id,
        "active_agent": status.active_agent,
        "agent_count": len(agents),
        "agents": agents
    }


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: str,
    limit: int = 50
) -> dict[str, Any]:
    """
    Get status messages for a session.

    Args:
        session_id: The session identifier
        limit: Maximum messages to return

    Returns:
        List of status messages
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    messages = status.messages[-limit:] if limit else status.messages

    return {
        "success": True,
        "session_id": session_id,
        "count": len(messages),
        "messages": messages
    }


@router.delete("/{session_id}")
def cleanup_session(session_id: str) -> dict[str, Any]:
    """
    Clean up a completed or errored session.

    Args:
        session_id: The session identifier

    Returns:
        Confirmation message
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if status.current_phase not in [ExecutionPhase.COMPLETED, ExecutionPhase.ERROR]:
        raise HTTPException(
            status_code=400,
            detail="Cannot cleanup active session. Wait for completion or error."
        )

    tracker.cleanup_session(session_id)

    return {
        "success": True,
        "message": f"Session '{session_id}' cleaned up"
    }


@router.get("/{session_id}/progress")
def get_session_progress(session_id: str) -> dict[str, Any]:
    """
    Get detailed progress information for a session.

    Args:
        session_id: The session identifier

    Returns:
        Progress breakdown by phase
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    phases = [
        {"name": "Initializing", "key": "initializing", "weight": 0.05},
        {"name": "Planning", "key": "planning", "weight": 0.10},
        {"name": "Researching", "key": "researching", "weight": 0.40},
        {"name": "Reviewing", "key": "reviewing", "weight": 0.10},
        {"name": "Coding", "key": "coding", "weight": 0.10},
        {"name": "Editing", "key": "editing", "weight": 0.20},
        {"name": "Finalizing", "key": "finalizing", "weight": 0.05},
    ]

    phase_details = []
    for phase in phases:
        progress = status.phase_progress.get(phase["key"], 0.0)
        is_current = status.current_phase.value == phase["key"]
        is_completed = progress >= 1.0

        phase_details.append({
            "name": phase["name"],
            "key": phase["key"],
            "progress": progress,
            "weight": phase["weight"],
            "is_current": is_current,
            "is_completed": is_completed,
            "status": "current" if is_current else ("completed" if is_completed else "pending")
        })

    return {
        "success": True,
        "session_id": session_id,
        "overall_progress": status.progress,
        "current_phase": status.current_phase.value,
        "phases": phase_details,
        "started_at": status.started_at.isoformat(),
        "estimated_completion": status.estimated_completion.isoformat() if status.estimated_completion else None
    }
