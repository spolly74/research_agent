"""
Tests for Execution Tracker
"""

import pytest
from datetime import datetime

from app.core.execution_tracker import (
    ExecutionTracker,
    ExecutionStatus,
    ExecutionPhase,
    EventType,
    get_execution_tracker,
    PHASE_WEIGHTS
)


class TestExecutionTracker:
    """Test ExecutionTracker functionality."""

    def setup_method(self):
        """Reset tracker state before each test."""
        # Clear all sessions
        tracker = get_execution_tracker()
        for session_id in list(tracker._sessions.keys()):
            tracker.cleanup_session(session_id)

    def test_singleton(self):
        """Test that ExecutionTracker is a singleton."""
        tracker1 = get_execution_tracker()
        tracker2 = get_execution_tracker()
        assert tracker1 is tracker2

    def test_start_session(self):
        """Test starting a new session."""
        tracker = get_execution_tracker()
        status = tracker.start_session("test-session-1", "Test query")

        assert status is not None
        assert status.session_id == "test-session-1"
        assert status.current_phase == ExecutionPhase.INITIALIZING
        assert status.progress == 0.0
        assert "Test query" in status.messages[0]

    def test_update_phase(self):
        """Test updating execution phase."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-2")

        tracker.update_phase("test-session-2", ExecutionPhase.PLANNING, "Creating plan")

        status = tracker.get_status("test-session-2")
        assert status.current_phase == ExecutionPhase.PLANNING
        assert "Creating plan" in status.messages

    def test_set_active_agent(self):
        """Test setting active agent."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-3")

        tracker.set_active_agent("test-session-3", "researcher", ["browser_search"])

        status = tracker.get_status("test-session-3")
        assert status.active_agent == "researcher"
        assert "browser_search" in status.active_tools
        assert status.current_agent_execution is not None
        assert status.current_agent_execution.agent_name == "researcher"

    def test_update_agent_progress(self):
        """Test updating agent progress."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-4")
        tracker.set_active_agent("test-session-4", "researcher")

        tracker.update_agent_progress("test-session-4", 0.5, "Searching...")

        status = tracker.get_status("test-session-4")
        assert status.current_agent_execution.progress == 0.5
        assert "Searching..." in status.messages

    def test_complete_agent(self):
        """Test completing an agent."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-5")
        tracker.set_active_agent("test-session-5", "researcher")

        tracker.complete_agent("test-session-5", "Found 5 sources")

        status = tracker.get_status("test-session-5")
        assert status.active_agent is None
        assert status.current_agent_execution is None
        assert len(status.agent_history) == 1
        assert status.agent_history[0].agent_name == "researcher"
        assert status.agent_history[0].status == "completed"

    def test_record_tool_invocation(self):
        """Test recording tool invocations."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-6")
        tracker.set_active_agent("test-session-6", "researcher")

        tracker.record_tool_invocation("test-session-6", "browser_search", {"query": "test"})

        status = tracker.get_status("test-session-6")
        assert len(status.current_agent_execution.tools_used) == 1
        assert status.current_agent_execution.tools_used[0].tool_name == "browser_search"

    def test_record_tool_completion(self):
        """Test recording tool completion."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-7")
        tracker.set_active_agent("test-session-7", "researcher")
        tracker.record_tool_invocation("test-session-7", "browser_search", {"query": "test"})

        tracker.record_tool_completion("test-session-7", "browser_search", "Found results", True)

        status = tracker.get_status("test-session-7")
        tool_exec = status.current_agent_execution.tools_used[0]
        assert tool_exec.completed_at is not None
        assert tool_exec.result_summary == "Found results"
        assert tool_exec.success == True

    def test_complete_session(self):
        """Test completing a session."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-8")

        tracker.complete_session("test-session-8", "Final report generated")

        status = tracker.get_status("test-session-8")
        assert status.current_phase == ExecutionPhase.COMPLETED
        assert status.progress == 1.0
        assert status.completed_at is not None

    def test_record_error(self):
        """Test recording errors."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-9")

        tracker.record_error("test-session-9", "Something went wrong", recoverable=False)

        status = tracker.get_status("test-session-9")
        assert status.error == "Something went wrong"
        assert status.current_phase == ExecutionPhase.ERROR

    def test_record_recoverable_error(self):
        """Test recording recoverable errors."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-10")
        tracker.update_phase("test-session-10", ExecutionPhase.RESEARCHING)

        tracker.record_error("test-session-10", "Temporary failure", recoverable=True)

        status = tracker.get_status("test-session-10")
        assert status.error == "Temporary failure"
        assert status.current_phase == ExecutionPhase.RESEARCHING  # Phase not changed

    def test_set_plan(self):
        """Test setting the plan."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-11")

        plan = {
            "main_goal": "Research AI trends",
            "tasks": [
                {"id": 1, "description": "Search web", "assigned_agent": "researcher"},
                {"id": 2, "description": "Write report", "assigned_agent": "editor"}
            ]
        }
        tracker.set_plan("test-session-11", plan)

        status = tracker.get_status("test-session-11")
        assert status.plan is not None
        assert status.plan["main_goal"] == "Research AI trends"

    def test_to_dict(self):
        """Test serialization to dict."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-12")
        tracker.set_active_agent("test-session-12", "researcher")

        status = tracker.get_status("test-session-12")
        data = status.to_dict()

        assert data["session_id"] == "test-session-12"
        assert data["current_phase"] == "initializing"
        assert data["active_agent"] == "researcher"
        assert "started_at" in data
        assert "updated_at" in data

    def test_cleanup_session(self):
        """Test session cleanup."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-13")

        assert tracker.get_status("test-session-13") is not None

        tracker.cleanup_session("test-session-13")

        assert tracker.get_status("test-session-13") is None

    def test_get_all_sessions(self):
        """Test getting all sessions."""
        tracker = get_execution_tracker()

        # Clean up any existing sessions
        for sid in list(tracker._sessions.keys()):
            tracker.cleanup_session(sid)

        tracker.start_session("test-session-a")
        tracker.start_session("test-session-b")

        all_sessions = tracker.get_all_sessions()
        assert len(all_sessions) == 2
        assert "test-session-a" in all_sessions
        assert "test-session-b" in all_sessions

    def test_progress_calculation(self):
        """Test progress calculation based on phases."""
        tracker = get_execution_tracker()
        tracker.start_session("test-session-14")

        # Start planning
        tracker.update_phase("test-session-14", ExecutionPhase.PLANNING)
        status = tracker.get_status("test-session-14")

        # Progress should be at least the weight of INITIALIZING
        assert status.progress >= PHASE_WEIGHTS[ExecutionPhase.INITIALIZING]

        # Complete planning, move to researching
        tracker.update_phase("test-session-14", ExecutionPhase.RESEARCHING)
        status = tracker.get_status("test-session-14")

        # Progress should include INITIALIZING + PLANNING weights
        expected_min = PHASE_WEIGHTS[ExecutionPhase.INITIALIZING] + PHASE_WEIGHTS[ExecutionPhase.PLANNING]
        assert status.progress >= expected_min


class TestEventEmission:
    """Test event emission functionality."""

    def setup_method(self):
        """Reset tracker state before each test."""
        tracker = get_execution_tracker()
        for session_id in list(tracker._sessions.keys()):
            tracker.cleanup_session(session_id)
        # Clear handlers
        tracker._event_handlers = []
        tracker._async_event_handlers = []

    def test_event_handler_registration(self):
        """Test registering event handlers."""
        tracker = get_execution_tracker()
        events_received = []

        def handler(session_id, event_type, data):
            events_received.append((session_id, event_type, data))

        tracker.register_event_handler(handler)
        tracker.start_session("test-event-1")

        assert len(events_received) == 1
        assert events_received[0][0] == "test-event-1"
        assert events_received[0][1] == EventType.SESSION_STARTED

    def test_multiple_events(self):
        """Test that multiple events are emitted."""
        tracker = get_execution_tracker()
        events_received = []

        def handler(session_id, event_type, data):
            events_received.append(event_type)

        tracker.register_event_handler(handler)

        tracker.start_session("test-event-2")
        tracker.update_phase("test-event-2", ExecutionPhase.PLANNING)
        tracker.set_active_agent("test-event-2", "orchestrator")
        tracker.complete_agent("test-event-2", "Done")

        assert EventType.SESSION_STARTED in events_received
        assert EventType.PHASE_CHANGED in events_received
        assert EventType.AGENT_STARTED in events_received
        assert EventType.AGENT_COMPLETED in events_received


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
