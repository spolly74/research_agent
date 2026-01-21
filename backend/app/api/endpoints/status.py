"""
Status API Endpoints

Provides REST endpoints for:
- Polling session status (fallback to WebSocket)
- Listing active sessions
- Session history
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Optional
import structlog

from app.core.execution_tracker import get_execution_tracker, ExecutionPhase, PlanApprovalStatus
from app.core.database import SessionLocal
from app.models.graph_state import SessionRecovery, GraphCheckpoint


# Request models for plan management
class TaskUpdate(BaseModel):
    """Request body for updating a task."""
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    status: Optional[str] = None
    dependencies: Optional[list[int]] = None


class TaskCreate(BaseModel):
    """Request body for creating a task."""
    description: str
    assigned_agent: str
    dependencies: Optional[list[int]] = None
    position: Optional[int] = None


class TaskReorder(BaseModel):
    """Request body for reordering tasks."""
    task_order: list[int]


class PlanApproval(BaseModel):
    """Request body for approving/rejecting a plan."""
    approved: bool
    modifications: Optional[dict] = None

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
        Current execution status or pending status if not yet tracking
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        # Return a pending status instead of 404 - session may be starting up
        return {
            "success": True,
            "session_id": session_id,
            "status": {
                "session_id": session_id,
                "current_phase": "initializing",
                "progress": 0,
                "active_agent": None,
                "active_tools": [],
                "plan": None,
                "plan_approval_status": "pending",
                "plan_waiting_approval": False,
                "started_at": None,
                "updated_at": None,
                "completed_at": None,
                "error": None,
                "messages": ["Waiting for session to start..."],
                "phase_progress": {},
                "estimated_completion": None,
                "agent_history": []
            }
        }

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
        The orchestrator's plan or empty if not yet created
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status or not status.plan:
        # Return empty plan instead of 404
        return {
            "success": True,
            "session_id": session_id,
            "plan": None,
            "approval_status": "pending",
            "waiting_approval": False
        }

    return {
        "success": True,
        "session_id": session_id,
        "plan": status.plan,
        "approval_status": status.plan_approval_status.value,
        "waiting_approval": status.plan_waiting_approval
    }


@router.put("/{session_id}/plan/task/{task_id}")
def update_plan_task(session_id: str, task_id: int, task_update: TaskUpdate) -> dict[str, Any]:
    """
    Update a specific task in the plan.

    Args:
        session_id: The session identifier
        task_id: The task ID to update
        task_update: The fields to update

    Returns:
        Updated task
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not status.plan:
        raise HTTPException(status_code=404, detail="No plan exists for this session")

    # Convert to dict, excluding None values
    updates = {k: v for k, v in task_update.model_dump().items() if v is not None}

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    updated_task = tracker.update_plan_task(session_id, task_id, updates)

    if not updated_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "success": True,
        "session_id": session_id,
        "task": updated_task
    }


@router.post("/{session_id}/plan/task")
def add_plan_task(session_id: str, task_create: TaskCreate) -> dict[str, Any]:
    """
    Add a new task to the plan.

    Args:
        session_id: The session identifier
        task_create: The task to create

    Returns:
        Created task
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    new_task = tracker.add_plan_task(
        session_id=session_id,
        description=task_create.description,
        assigned_agent=task_create.assigned_agent,
        dependencies=task_create.dependencies,
        position=task_create.position
    )

    if not new_task:
        raise HTTPException(status_code=500, detail="Failed to create task")

    return {
        "success": True,
        "session_id": session_id,
        "task": new_task
    }


@router.delete("/{session_id}/plan/task/{task_id}")
def remove_plan_task(session_id: str, task_id: int) -> dict[str, Any]:
    """
    Remove a task from the plan.

    Args:
        session_id: The session identifier
        task_id: The task ID to remove

    Returns:
        Success confirmation
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not status.plan:
        raise HTTPException(status_code=404, detail="No plan exists for this session")

    success = tracker.remove_plan_task(session_id, task_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return {
        "success": True,
        "session_id": session_id,
        "message": f"Task {task_id} removed"
    }


@router.put("/{session_id}/plan/reorder")
def reorder_plan_tasks(session_id: str, reorder: TaskReorder) -> dict[str, Any]:
    """
    Reorder tasks in the plan.

    Args:
        session_id: The session identifier
        reorder: The new task order

    Returns:
        Updated plan
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not status.plan:
        raise HTTPException(status_code=404, detail="No plan exists for this session")

    success = tracker.reorder_plan_tasks(session_id, reorder.task_order)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid task order - all task IDs must be present")

    return {
        "success": True,
        "session_id": session_id,
        "plan": status.plan
    }


@router.post("/{session_id}/plan/approve")
def approve_plan(session_id: str, approval: PlanApproval) -> dict[str, Any]:
    """
    Approve or reject the research plan.

    Args:
        session_id: The session identifier
        approval: Approval decision and optional modifications

    Returns:
        Approval result
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")

    if not status.plan:
        raise HTTPException(status_code=404, detail="No plan exists for this session")

    success = tracker.approve_plan(
        session_id=session_id,
        approved=approval.approved,
        modifications=approval.modifications
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update plan approval status")

    return {
        "success": True,
        "session_id": session_id,
        "approved": approval.approved,
        "approval_status": tracker.get_status(session_id).plan_approval_status.value
    }


@router.get("/{session_id}/agents")
def get_session_agents(session_id: str) -> dict[str, Any]:
    """
    Get the agent execution history for a session.

    Args:
        session_id: The session identifier

    Returns:
        List of agent executions or empty if not yet tracking
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        # Return empty agents list instead of 404
        return {
            "success": True,
            "session_id": session_id,
            "active_agent": None,
            "agent_count": 0,
            "agents": []
        }

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
        List of status messages or empty if not yet tracking
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    if not status:
        return {
            "success": True,
            "session_id": session_id,
            "count": 0,
            "messages": []
        }

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
        Progress breakdown by phase or initial state if not yet tracking
    """
    tracker = get_execution_tracker()
    status = tracker.get_status(session_id)

    phases = [
        {"name": "Initializing", "key": "initializing", "weight": 0.05},
        {"name": "Planning", "key": "planning", "weight": 0.10},
        {"name": "Researching", "key": "researching", "weight": 0.40},
        {"name": "Reviewing", "key": "reviewing", "weight": 0.10},
        {"name": "Coding", "key": "coding", "weight": 0.10},
        {"name": "Editing", "key": "editing", "weight": 0.20},
        {"name": "Finalizing", "key": "finalizing", "weight": 0.05},
    ]

    # If no status yet, return initial state with all phases pending
    if not status:
        phase_details = []
        for i, phase in enumerate(phases):
            phase_details.append({
                "name": phase["name"],
                "key": phase["key"],
                "progress": 0.0,
                "weight": phase["weight"],
                "is_current": i == 0,  # First phase is current
                "is_completed": False,
                "status": "current" if i == 0 else "pending"
            })
        return {
            "success": True,
            "session_id": session_id,
            "overall_progress": 0.0,
            "current_phase": "initializing",
            "phases": phase_details,
            "started_at": None,
            "estimated_completion": None
        }

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


@router.get("/{session_id}/recovery")
def get_session_recovery_info(session_id: str) -> dict[str, Any]:
    """
    Get recovery information for a session.

    Used to check if a session can be resumed after a server restart.

    Args:
        session_id: The session identifier

    Returns:
        Recovery status and checkpoint information
    """
    db = SessionLocal()
    try:
        # Look up recovery record
        recovery = db.query(SessionRecovery).filter(
            SessionRecovery.session_id == session_id
        ).first()

        if not recovery:
            return {
                "success": True,
                "session_id": session_id,
                "recoverable": False,
                "reason": "No recovery record found"
            }

        # Check if checkpoint exists
        has_checkpoint = False
        if recovery.last_checkpoint_id:
            checkpoint = db.query(GraphCheckpoint).filter(
                GraphCheckpoint.thread_id == recovery.thread_id,
                GraphCheckpoint.checkpoint_id == recovery.last_checkpoint_id
            ).first()
            has_checkpoint = checkpoint is not None

        return {
            "success": True,
            "session_id": session_id,
            "recoverable": has_checkpoint and recovery.status != "completed",
            "status": recovery.status,
            "last_phase": recovery.last_phase,
            "last_checkpoint_id": recovery.last_checkpoint_id,
            "retry_count": recovery.retry_count,
            "last_activity": recovery.last_activity_at.isoformat() if recovery.last_activity_at else None,
            "thread_id": recovery.thread_id
        }
    finally:
        db.close()


@router.post("/{session_id}/recover")
def recover_session(session_id: str) -> dict[str, Any]:
    """
    Attempt to recover a session from its last checkpoint.

    This resumes execution from where the session left off.

    Args:
        session_id: The session identifier

    Returns:
        Recovery result
    """
    from app.agents.graph import graph, can_resume_session, get_session_state

    db = SessionLocal()
    try:
        # Get recovery info
        recovery = db.query(SessionRecovery).filter(
            SessionRecovery.session_id == session_id
        ).first()

        if not recovery:
            raise HTTPException(
                status_code=404,
                detail=f"No recovery record for session '{session_id}'"
            )

        if recovery.status == "completed":
            raise HTTPException(
                status_code=400,
                detail="Session already completed, cannot recover"
            )

        thread_id = recovery.thread_id

        # Check if we can resume
        if not can_resume_session(thread_id):
            raise HTTPException(
                status_code=400,
                detail="Session state not available for recovery"
            )

        # Get the current state
        state = get_session_state(thread_id)

        # Restart execution tracker
        tracker = get_execution_tracker()
        tracker.start_session(session_id, "Recovered session")

        # Update recovery record
        recovery.retry_count += 1
        recovery.status = "recovering"
        db.commit()

        # Continue execution from checkpoint
        config = {"configurable": {"thread_id": thread_id}}

        try:
            # Resume the graph
            result = graph.invoke(None, config=config)

            # Update tracking
            final_content = result.get("final_report", "")
            tracker.complete_session(session_id, final_content[:200] if final_content else "")

            # Update recovery status
            recovery.status = "completed"
            db.commit()

            return {
                "success": True,
                "session_id": session_id,
                "message": "Session recovered and completed",
                "result_preview": final_content[:500] if final_content else None
            }

        except Exception as e:
            # Record error
            tracker.record_error(session_id, str(e), recoverable=True)
            recovery.status = "error"
            recovery.error_message = str(e)
            db.commit()

            raise HTTPException(
                status_code=500,
                detail=f"Recovery failed: {str(e)}"
            )

    finally:
        db.close()


@router.get("/recoverable")
def list_recoverable_sessions(limit: int = 20) -> dict[str, Any]:
    """
    List all sessions that can potentially be recovered.

    Args:
        limit: Maximum number of sessions to return

    Returns:
        List of recoverable sessions
    """
    db = SessionLocal()
    try:
        recoverable = db.query(SessionRecovery).filter(
            SessionRecovery.status.in_(["active", "error", "recovering"])
        ).order_by(
            SessionRecovery.last_activity_at.desc()
        ).limit(limit).all()

        sessions = []
        for r in recoverable:
            # Check if checkpoint still exists
            has_checkpoint = db.query(GraphCheckpoint).filter(
                GraphCheckpoint.thread_id == r.thread_id,
                GraphCheckpoint.checkpoint_id == r.last_checkpoint_id
            ).first() is not None

            if has_checkpoint:
                sessions.append({
                    "session_id": r.session_id,
                    "thread_id": r.thread_id,
                    "status": r.status,
                    "last_phase": r.last_phase,
                    "retry_count": r.retry_count,
                    "last_activity": r.last_activity_at.isoformat() if r.last_activity_at else None,
                    "error": r.error_message
                })

        return {
            "success": True,
            "count": len(sessions),
            "sessions": sessions
        }
    finally:
        db.close()
