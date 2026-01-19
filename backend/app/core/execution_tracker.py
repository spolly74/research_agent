"""
Execution Tracker

Tracks the execution status of research sessions and emits events
for real-time progress updates to the frontend.

Features:
- Session lifecycle tracking (start, progress, complete, error)
- Phase and agent tracking
- Tool invocation tracking
- Progress estimation
- WebSocket event emission
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any
import asyncio
import structlog
from threading import Lock

logger = structlog.get_logger(__name__)


class ExecutionPhase(str, Enum):
    """Phases of research execution."""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    RESEARCHING = "researching"
    REVIEWING = "reviewing"
    CODING = "coding"
    EDITING = "editing"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"


class EventType(str, Enum):
    """Types of events that can be emitted."""
    SESSION_STARTED = "session.started"
    SESSION_COMPLETED = "session.completed"
    SESSION_ERROR = "session.error"
    PHASE_CHANGED = "phase.changed"
    AGENT_STARTED = "agent.started"
    AGENT_PROGRESS = "agent.progress"
    AGENT_COMPLETED = "agent.completed"
    TOOL_INVOKED = "tool.invoked"
    TOOL_COMPLETED = "tool.completed"
    PLAN_CREATED = "plan.created"
    PLAN_UPDATED = "plan.updated"
    PLAN_APPROVED = "plan.approved"
    TASK_UPDATED = "task.updated"


class PlanApprovalStatus(str, Enum):
    """Plan approval states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    tool_name: str
    args: dict
    started_at: datetime
    completed_at: Optional[datetime] = None
    result_summary: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class AgentExecution:
    """Record of an agent execution."""
    agent_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    tools_used: list[ToolExecution] = field(default_factory=list)
    progress: float = 0.0
    status: str = "running"
    result_summary: Optional[str] = None


@dataclass
class ExecutionStatus:
    """Current execution state for a research session."""
    session_id: str
    current_phase: ExecutionPhase = ExecutionPhase.INITIALIZING
    plan: Optional[dict] = None
    plan_approval_status: PlanApprovalStatus = PlanApprovalStatus.PENDING
    plan_waiting_approval: bool = False
    active_agent: Optional[str] = None
    active_tools: list[str] = field(default_factory=list)
    progress: float = 0.0
    phase_progress: dict[str, float] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    error: Optional[str] = None
    agent_history: list[AgentExecution] = field(default_factory=list)
    current_agent_execution: Optional[AgentExecution] = None
    messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "current_phase": self.current_phase.value,
            "plan": self.plan,
            "plan_approval_status": self.plan_approval_status.value,
            "plan_waiting_approval": self.plan_waiting_approval,
            "active_agent": self.active_agent,
            "active_tools": self.active_tools,
            "progress": self.progress,
            "phase_progress": self.phase_progress,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "error": self.error,
            "agent_history": [
                {
                    "agent": a.agent_name,
                    "started_at": a.started_at.isoformat(),
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None,
                    "tools_used": len(a.tools_used),
                    "status": a.status
                }
                for a in self.agent_history
            ],
            "messages": self.messages[-10:]  # Last 10 messages
        }


# Phase weights for progress calculation
PHASE_WEIGHTS = {
    ExecutionPhase.INITIALIZING: 0.05,
    ExecutionPhase.PLANNING: 0.10,
    ExecutionPhase.RESEARCHING: 0.40,
    ExecutionPhase.REVIEWING: 0.10,
    ExecutionPhase.CODING: 0.10,
    ExecutionPhase.EDITING: 0.20,
    ExecutionPhase.FINALIZING: 0.05,
}


class ExecutionTracker:
    """
    Manages execution status across all sessions.

    Thread-safe singleton that tracks session progress and emits events.

    Usage:
        tracker = get_execution_tracker()
        tracker.start_session("session-123")
        tracker.update_phase("session-123", ExecutionPhase.RESEARCHING)
        tracker.set_active_agent("session-123", "researcher", ["browser_search"])
        status = tracker.get_status("session-123")
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._sessions: dict[str, ExecutionStatus] = {}
        self._event_handlers: list[Callable[[str, EventType, dict], None]] = []
        self._async_event_handlers: list[Callable[[str, EventType, dict], Any]] = []
        self._session_lock = Lock()
        self._initialized = True

        logger.info("ExecutionTracker initialized")

    def register_event_handler(self, handler: Callable[[str, EventType, dict], None]) -> None:
        """Register a synchronous event handler."""
        self._event_handlers.append(handler)
        logger.debug("Registered sync event handler", handler_count=len(self._event_handlers))

    def register_async_event_handler(self, handler: Callable[[str, EventType, dict], Any]) -> None:
        """Register an async event handler (for WebSocket emission)."""
        self._async_event_handlers.append(handler)
        logger.debug("Registered async event handler", handler_count=len(self._async_event_handlers))

    def _emit_event(self, session_id: str, event_type: EventType, payload: dict) -> None:
        """Emit an event to all registered handlers."""
        event_data = {
            "session_id": session_id,
            "event_type": event_type.value,
            "timestamp": datetime.now().isoformat(),
            "payload": payload
        }

        # Call sync handlers
        for handler in self._event_handlers:
            try:
                handler(session_id, event_type, event_data)
            except Exception as e:
                logger.error("Event handler error", error=str(e), event_type=event_type.value)

        # Schedule async handlers
        for handler in self._async_event_handlers:
            try:
                # Try to get running loop, create task if available
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(handler(session_id, event_type, event_data))
                except RuntimeError:
                    # No running loop, skip async handlers
                    pass
            except Exception as e:
                logger.error("Async event handler error", error=str(e), event_type=event_type.value)

        logger.debug(
            "Event emitted",
            session_id=session_id,
            event_type=event_type.value
        )

    def start_session(self, session_id: str, initial_message: str = "") -> ExecutionStatus:
        """
        Initialize tracking for a new session.

        Args:
            session_id: Unique session identifier
            initial_message: Initial user message

        Returns:
            The new ExecutionStatus
        """
        with self._session_lock:
            status = ExecutionStatus(
                session_id=session_id,
                current_phase=ExecutionPhase.INITIALIZING,
                started_at=datetime.now()
            )

            if initial_message:
                status.messages.append(f"User: {initial_message[:100]}...")

            self._sessions[session_id] = status

        logger.info("Session started", session_id=session_id)

        self._emit_event(session_id, EventType.SESSION_STARTED, {
            "initial_message": initial_message[:100] if initial_message else None
        })

        return status

    def update_phase(self, session_id: str, phase: ExecutionPhase, message: str = "") -> None:
        """
        Update current execution phase.

        Args:
            session_id: Session to update
            phase: New phase
            message: Optional status message
        """
        with self._session_lock:
            if session_id not in self._sessions:
                logger.warning("Session not found", session_id=session_id)
                return

            status = self._sessions[session_id]
            old_phase = status.current_phase
            status.current_phase = phase
            status.updated_at = datetime.now()

            # Mark phase progress
            status.phase_progress[old_phase.value] = 1.0

            # Update overall progress
            status.progress = self._calculate_progress(status)

            if message:
                status.messages.append(message)

        logger.info(
            "Phase changed",
            session_id=session_id,
            old_phase=old_phase.value,
            new_phase=phase.value,
            progress=status.progress
        )

        self._emit_event(session_id, EventType.PHASE_CHANGED, {
            "old_phase": old_phase.value,
            "new_phase": phase.value,
            "progress": status.progress,
            "message": message
        })

    def set_plan(self, session_id: str, plan: dict, require_approval: bool = False) -> None:
        """
        Set the orchestrator's plan for the session.

        Args:
            session_id: Session to update
            plan: The plan dictionary
            require_approval: Whether to wait for user approval before proceeding
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            status.plan = plan
            status.plan_waiting_approval = require_approval
            status.plan_approval_status = PlanApprovalStatus.PENDING if require_approval else PlanApprovalStatus.APPROVED
            status.updated_at = datetime.now()
            status.messages.append(f"Plan created: {plan.get('main_goal', 'Unknown goal')}")

        self._emit_event(session_id, EventType.PLAN_CREATED, {
            "main_goal": plan.get("main_goal"),
            "task_count": len(plan.get("tasks", [])),
            "scope": plan.get("scope", {}).get("scope", "standard"),
            "require_approval": require_approval
        })

    def update_plan_task(
        self,
        session_id: str,
        task_id: int,
        updates: dict
    ) -> Optional[dict]:
        """
        Update a specific task in the plan.

        Args:
            session_id: Session to update
            task_id: ID of the task to update
            updates: Dictionary of fields to update

        Returns:
            Updated task or None if not found
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return None

            status = self._sessions[session_id]
            if not status.plan or "tasks" not in status.plan:
                return None

            # Find and update the task
            for task in status.plan["tasks"]:
                if task.get("id") == task_id:
                    # Update allowed fields
                    allowed_fields = ["description", "assigned_agent", "status", "dependencies"]
                    for field in allowed_fields:
                        if field in updates:
                            task[field] = updates[field]

                    status.updated_at = datetime.now()
                    status.messages.append(f"Task {task_id} updated")

                    self._emit_event(session_id, EventType.TASK_UPDATED, {
                        "task_id": task_id,
                        "updates": updates
                    })

                    return task

            return None

    def add_plan_task(
        self,
        session_id: str,
        description: str,
        assigned_agent: str,
        dependencies: list[int] = None,
        position: int = None
    ) -> Optional[dict]:
        """
        Add a new task to the plan.

        Args:
            session_id: Session to update
            description: Task description
            assigned_agent: Agent to assign
            dependencies: List of task IDs this depends on
            position: Position to insert (None for end)

        Returns:
            The new task or None if failed
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return None

            status = self._sessions[session_id]
            if not status.plan:
                status.plan = {"main_goal": "", "tasks": []}

            if "tasks" not in status.plan:
                status.plan["tasks"] = []

            # Generate new task ID
            existing_ids = [t.get("id", 0) for t in status.plan["tasks"]]
            new_id = max(existing_ids, default=0) + 1

            new_task = {
                "id": new_id,
                "description": description,
                "assigned_agent": assigned_agent,
                "status": "pending",
                "dependencies": dependencies or []
            }

            # Insert at position or append
            if position is not None and 0 <= position <= len(status.plan["tasks"]):
                status.plan["tasks"].insert(position, new_task)
            else:
                status.plan["tasks"].append(new_task)

            status.updated_at = datetime.now()
            status.messages.append(f"Task added: {description[:50]}")

            self._emit_event(session_id, EventType.PLAN_UPDATED, {
                "action": "task_added",
                "task": new_task
            })

            return new_task

    def remove_plan_task(self, session_id: str, task_id: int) -> bool:
        """
        Remove a task from the plan.

        Args:
            session_id: Session to update
            task_id: ID of the task to remove

        Returns:
            True if removed, False if not found
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return False

            status = self._sessions[session_id]
            if not status.plan or "tasks" not in status.plan:
                return False

            original_count = len(status.plan["tasks"])
            status.plan["tasks"] = [
                t for t in status.plan["tasks"]
                if t.get("id") != task_id
            ]

            if len(status.plan["tasks"]) < original_count:
                # Also remove this task from dependencies of other tasks
                for task in status.plan["tasks"]:
                    if task.get("dependencies"):
                        task["dependencies"] = [
                            d for d in task["dependencies"]
                            if d != task_id
                        ]

                status.updated_at = datetime.now()
                status.messages.append(f"Task {task_id} removed")

                self._emit_event(session_id, EventType.PLAN_UPDATED, {
                    "action": "task_removed",
                    "task_id": task_id
                })

                return True

            return False

    def reorder_plan_tasks(
        self,
        session_id: str,
        task_order: list[int]
    ) -> bool:
        """
        Reorder tasks in the plan.

        Args:
            session_id: Session to update
            task_order: List of task IDs in desired order

        Returns:
            True if reordered, False if failed
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return False

            status = self._sessions[session_id]
            if not status.plan or "tasks" not in status.plan:
                return False

            # Build lookup of tasks by ID
            task_lookup = {t.get("id"): t for t in status.plan["tasks"]}

            # Verify all IDs exist
            if set(task_order) != set(task_lookup.keys()):
                return False

            # Reorder
            status.plan["tasks"] = [task_lookup[tid] for tid in task_order]
            status.updated_at = datetime.now()
            status.messages.append("Tasks reordered")

            self._emit_event(session_id, EventType.PLAN_UPDATED, {
                "action": "tasks_reordered",
                "new_order": task_order
            })

            return True

    def approve_plan(
        self,
        session_id: str,
        approved: bool = True,
        modifications: dict = None
    ) -> bool:
        """
        Approve or reject the plan.

        Args:
            session_id: Session to update
            approved: Whether to approve the plan
            modifications: Optional modifications to apply before approval

        Returns:
            True if successful, False if failed
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return False

            status = self._sessions[session_id]
            if not status.plan:
                return False

            # Apply any modifications
            if modifications:
                if "main_goal" in modifications:
                    status.plan["main_goal"] = modifications["main_goal"]
                if "tasks" in modifications:
                    status.plan["tasks"] = modifications["tasks"]
                status.plan_approval_status = PlanApprovalStatus.MODIFIED

            if approved:
                status.plan_approval_status = PlanApprovalStatus.APPROVED
                status.plan_waiting_approval = False
                status.messages.append("Plan approved")
            else:
                status.plan_approval_status = PlanApprovalStatus.REJECTED
                status.plan_waiting_approval = False
                status.messages.append("Plan rejected")

            status.updated_at = datetime.now()

        self._emit_event(session_id, EventType.PLAN_APPROVED, {
            "approved": approved,
            "modified": modifications is not None,
            "approval_status": status.plan_approval_status.value
        })

        return True

    def is_plan_approved(self, session_id: str) -> bool:
        """
        Check if the plan is approved.

        Args:
            session_id: Session to check

        Returns:
            True if plan is approved
        """
        status = self._sessions.get(session_id)
        if not status:
            return False
        return status.plan_approval_status in [
            PlanApprovalStatus.APPROVED,
            PlanApprovalStatus.MODIFIED
        ]

    def set_active_agent(
        self,
        session_id: str,
        agent: str,
        tools: list[str] = None
    ) -> None:
        """
        Update active agent and tools.

        Args:
            session_id: Session to update
            agent: Agent name (orchestrator, researcher, etc.)
            tools: List of tools available to the agent
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]

            # Complete previous agent if any
            if status.current_agent_execution:
                status.current_agent_execution.completed_at = datetime.now()
                status.current_agent_execution.status = "completed"
                status.agent_history.append(status.current_agent_execution)

            # Start new agent execution
            status.current_agent_execution = AgentExecution(
                agent_name=agent,
                started_at=datetime.now()
            )
            status.active_agent = agent
            status.active_tools = tools or []
            status.updated_at = datetime.now()
            status.messages.append(f"Agent started: {agent}")

        logger.info(
            "Agent started",
            session_id=session_id,
            agent=agent,
            tools=tools
        )

        self._emit_event(session_id, EventType.AGENT_STARTED, {
            "agent": agent,
            "tools": tools or []
        })

    def update_agent_progress(
        self,
        session_id: str,
        progress: float,
        detail: str = ""
    ) -> None:
        """
        Update progress for the current agent.

        Args:
            session_id: Session to update
            progress: Progress value 0.0 - 1.0
            detail: Optional detail message
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            if status.current_agent_execution:
                status.current_agent_execution.progress = progress

            # Update phase progress based on agent progress
            phase_key = status.current_phase.value
            status.phase_progress[phase_key] = progress
            status.progress = self._calculate_progress(status)
            status.updated_at = datetime.now()

            if detail:
                status.messages.append(detail)

        self._emit_event(session_id, EventType.AGENT_PROGRESS, {
            "agent": status.active_agent,
            "progress": progress,
            "detail": detail,
            "overall_progress": status.progress
        })

    def complete_agent(
        self,
        session_id: str,
        result_summary: str = ""
    ) -> None:
        """
        Mark the current agent as completed.

        Args:
            session_id: Session to update
            result_summary: Summary of agent's work
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            if status.current_agent_execution:
                status.current_agent_execution.completed_at = datetime.now()
                status.current_agent_execution.status = "completed"
                status.current_agent_execution.progress = 1.0
                status.current_agent_execution.result_summary = result_summary
                status.agent_history.append(status.current_agent_execution)
                status.current_agent_execution = None

            status.active_agent = None
            status.active_tools = []
            status.updated_at = datetime.now()

            if result_summary:
                status.messages.append(f"Agent completed: {result_summary[:100]}")

        self._emit_event(session_id, EventType.AGENT_COMPLETED, {
            "result_summary": result_summary
        })

    def record_tool_invocation(
        self,
        session_id: str,
        tool_name: str,
        args: dict
    ) -> None:
        """
        Record that a tool has been invoked.

        Args:
            session_id: Session to update
            tool_name: Name of the tool
            args: Arguments passed to the tool
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            tool_exec = ToolExecution(
                tool_name=tool_name,
                args=args,
                started_at=datetime.now()
            )

            if status.current_agent_execution:
                status.current_agent_execution.tools_used.append(tool_exec)

            if tool_name not in status.active_tools:
                status.active_tools.append(tool_name)

            status.updated_at = datetime.now()
            status.messages.append(f"Tool invoked: {tool_name}")

        logger.debug("Tool invoked", session_id=session_id, tool=tool_name)

        self._emit_event(session_id, EventType.TOOL_INVOKED, {
            "tool": tool_name,
            "args": {k: str(v)[:50] for k, v in args.items()}  # Truncate args
        })

    def record_tool_completion(
        self,
        session_id: str,
        tool_name: str,
        result_summary: str = "",
        success: bool = True,
        error: str = None
    ) -> None:
        """
        Record that a tool has completed.

        Args:
            session_id: Session to update
            tool_name: Name of the tool
            result_summary: Summary of the result
            success: Whether the tool succeeded
            error: Error message if failed
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]

            # Find and update the tool execution
            if status.current_agent_execution:
                for tool_exec in reversed(status.current_agent_execution.tools_used):
                    if tool_exec.tool_name == tool_name and tool_exec.completed_at is None:
                        tool_exec.completed_at = datetime.now()
                        tool_exec.result_summary = result_summary
                        tool_exec.success = success
                        tool_exec.error = error
                        break

            if tool_name in status.active_tools:
                status.active_tools.remove(tool_name)

            status.updated_at = datetime.now()

        self._emit_event(session_id, EventType.TOOL_COMPLETED, {
            "tool": tool_name,
            "success": success,
            "result_summary": result_summary[:100] if result_summary else None,
            "error": error
        })

    def complete_session(
        self,
        session_id: str,
        report_summary: str = ""
    ) -> None:
        """
        Mark a session as completed.

        Args:
            session_id: Session to complete
            report_summary: Summary of the final report
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            status.current_phase = ExecutionPhase.COMPLETED
            status.progress = 1.0
            status.completed_at = datetime.now()
            status.updated_at = datetime.now()
            status.active_agent = None
            status.active_tools = []
            status.messages.append("Session completed successfully")

        logger.info("Session completed", session_id=session_id)

        self._emit_event(session_id, EventType.SESSION_COMPLETED, {
            "report_summary": report_summary[:200] if report_summary else None,
            "duration_seconds": (status.completed_at - status.started_at).total_seconds()
        })

    def record_error(
        self,
        session_id: str,
        error: str,
        recoverable: bool = False
    ) -> None:
        """
        Record an error in the session.

        Args:
            session_id: Session to update
            error: Error message
            recoverable: Whether the error is recoverable
        """
        with self._session_lock:
            if session_id not in self._sessions:
                return

            status = self._sessions[session_id]
            status.error = error
            status.updated_at = datetime.now()
            status.messages.append(f"Error: {error}")

            if not recoverable:
                status.current_phase = ExecutionPhase.ERROR

        logger.error(
            "Session error",
            session_id=session_id,
            error=error,
            recoverable=recoverable
        )

        self._emit_event(session_id, EventType.SESSION_ERROR, {
            "error": error,
            "recoverable": recoverable
        })

    def get_status(self, session_id: str) -> Optional[ExecutionStatus]:
        """
        Get current execution status.

        Args:
            session_id: Session to get status for

        Returns:
            ExecutionStatus or None if not found
        """
        return self._sessions.get(session_id)

    def get_all_sessions(self) -> dict[str, ExecutionStatus]:
        """Get all active sessions."""
        return self._sessions.copy()

    def cleanup_session(self, session_id: str) -> None:
        """Remove a session from tracking."""
        with self._session_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info("Session cleaned up", session_id=session_id)

    def _calculate_progress(self, status: ExecutionStatus) -> float:
        """
        Calculate overall progress based on phase weights.

        Args:
            status: Current execution status

        Returns:
            Progress value 0.0 - 1.0
        """
        total_progress = 0.0

        for phase, weight in PHASE_WEIGHTS.items():
            phase_progress = status.phase_progress.get(phase.value, 0.0)
            total_progress += phase_progress * weight

        # Add current phase partial progress
        current_weight = PHASE_WEIGHTS.get(status.current_phase, 0.0)
        current_phase_progress = status.phase_progress.get(status.current_phase.value, 0.0)
        if current_phase_progress < 1.0:
            total_progress += current_phase_progress * current_weight

        return min(1.0, total_progress)


# Singleton accessor
_tracker_instance: Optional[ExecutionTracker] = None


def get_execution_tracker() -> ExecutionTracker:
    """Get the singleton ExecutionTracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ExecutionTracker()
    return _tracker_instance
