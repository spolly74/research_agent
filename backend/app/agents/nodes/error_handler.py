"""
Error Handler Node - Handles errors and recovery in the agent graph.

Provides:
- Graceful error handling
- Partial result recovery
- User-friendly error messages
- Automatic retry coordination
"""

import structlog
from typing import Optional, Dict, Any
from langchain_core.messages import SystemMessage, AIMessage

from app.agents.state import AgentState
from app.core.execution_tracker import get_execution_tracker, ExecutionPhase

logger = structlog.get_logger(__name__)


# Error categories and their handling strategies
ERROR_STRATEGIES = {
    "llm_timeout": {
        "recoverable": True,
        "max_retries": 2,
        "message": "The AI service is temporarily slow. Retrying with simplified request.",
        "action": "retry_simplified",
    },
    "llm_overloaded": {
        "recoverable": True,
        "max_retries": 2,
        "message": "The AI service is currently overloaded. Waiting before retry.",
        "action": "retry_with_delay",
    },
    "tool_failure": {
        "recoverable": True,
        "max_retries": 1,
        "message": "A tool operation failed. Attempting alternative approach.",
        "action": "skip_tool",
    },
    "parsing_error": {
        "recoverable": True,
        "max_retries": 1,
        "message": "Response parsing failed. Retrying with explicit format instructions.",
        "action": "retry_with_format",
    },
    "context_exceeded": {
        "recoverable": True,
        "max_retries": 0,
        "message": "The request is too complex. Simplifying the approach.",
        "action": "simplify",
    },
    "rate_limit": {
        "recoverable": True,
        "max_retries": 3,
        "message": "API rate limit reached. Waiting before retry.",
        "action": "retry_with_backoff",
    },
    "unknown": {
        "recoverable": False,
        "max_retries": 0,
        "message": "An unexpected error occurred.",
        "action": "report",
    },
}


def categorize_error(error: Exception) -> str:
    """
    Categorize an error into a known category.

    Args:
        error: The exception to categorize

    Returns:
        Error category string
    """
    error_str = str(error).lower()

    if "timeout" in error_str:
        return "llm_timeout"

    if "overloaded" in error_str or "503" in error_str:
        return "llm_overloaded"

    if "tool" in error_str and ("failed" in error_str or "error" in error_str):
        return "tool_failure"

    if "parse" in error_str or "json" in error_str or "format" in error_str:
        return "parsing_error"

    if "context" in error_str and ("length" in error_str or "exceeded" in error_str):
        return "context_exceeded"

    if "rate" in error_str and "limit" in error_str:
        return "rate_limit"

    return "unknown"


def error_handler_node(state: AgentState) -> Dict[str, Any]:
    """
    Error handler node for the agent graph.

    Analyzes errors and determines recovery strategy.

    Args:
        state: Current agent state

    Returns:
        Updated state with error handling information
    """
    session_id = state.get("session_id")
    tracker = get_execution_tracker()

    # Get the last error from state (would be set by the failing node)
    last_error = state.get("last_error")
    error_count = state.get("error_count", 0)
    failed_node = state.get("failed_node", "unknown")

    logger.info(
        "Error handler invoked",
        session_id=session_id,
        failed_node=failed_node,
        error_count=error_count,
        error=last_error,
    )

    # Update tracking
    if session_id:
        tracker.set_active_agent(session_id, "error_handler")

    if last_error is None:
        # No error to handle
        logger.warning("Error handler called but no error found")
        return {"next_step": "CONTINUE"}

    # Categorize and get strategy
    error_category = categorize_error(Exception(last_error))
    strategy = ERROR_STRATEGIES.get(error_category, ERROR_STRATEGIES["unknown"])

    logger.info(
        "Error categorized",
        category=error_category,
        strategy=strategy["action"],
        recoverable=strategy["recoverable"],
    )

    # Check if we've exceeded retries
    if error_count >= strategy["max_retries"]:
        logger.warning(
            "Max retries exceeded",
            error_count=error_count,
            max_retries=strategy["max_retries"],
        )
        strategy = {
            **strategy,
            "recoverable": False,
            "message": f"{strategy['message']} Maximum retries exceeded.",
        }

    # Update tracking with error info
    if session_id:
        tracker.record_error(
            session_id,
            f"{strategy['message']} (Category: {error_category})",
            recoverable=strategy["recoverable"],
        )

    if not strategy["recoverable"]:
        # Generate error report for user
        error_report = _generate_error_report(
            state, error_category, strategy, last_error
        )

        if session_id:
            tracker.update_phase(session_id, ExecutionPhase.ERROR, "Research failed")

        return {
            "final_report": error_report,
            "next_step": "ERROR_FINAL",
            "error_handled": True,
        }

    # Attempt recovery
    recovery_result = _attempt_recovery(state, error_category, strategy)

    if session_id and recovery_result.get("recovered"):
        tracker.update_agent_progress(
            session_id, 0.5, f"Recovered from {error_category}"
        )

    return {
        **recovery_result,
        "error_count": error_count + 1,
        "last_error": None,  # Clear the error
    }


def _generate_error_report(
    state: AgentState,
    error_category: str,
    strategy: Dict[str, Any],
    error_message: str,
) -> str:
    """Generate a user-friendly error report."""
    # Check if we have any partial results
    research_data = state.get("research_data", [])
    has_partial_results = bool(research_data and any(r for r in research_data if r))

    report_parts = [
        "# Research Report - Incomplete",
        "",
        "Unfortunately, the research could not be fully completed due to an error.",
        "",
        f"**Error Type:** {error_category.replace('_', ' ').title()}",
        f"**Status:** {strategy['message']}",
        "",
    ]

    if has_partial_results:
        report_parts.extend([
            "## Partial Results",
            "",
            "Some research was completed before the error occurred:",
            "",
        ])
        for i, data in enumerate(research_data, 1):
            if data:
                report_parts.append(f"### Finding {i}")
                report_parts.append(data[:500] + "..." if len(data) > 500 else data)
                report_parts.append("")

    report_parts.extend([
        "## Recommendations",
        "",
        "- Try running the research again",
        "- Simplify your research query",
        "- Check if the required services are available",
        "",
        "---",
        "*This report was generated after encountering an unrecoverable error.*",
    ])

    return "\n".join(report_parts)


def _attempt_recovery(
    state: AgentState,
    error_category: str,
    strategy: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Attempt to recover from an error.

    Args:
        state: Current agent state
        error_category: The categorized error type
        strategy: The recovery strategy

    Returns:
        State updates for recovery
    """
    action = strategy["action"]
    logger.info("Attempting recovery", action=action)

    if action == "retry_simplified":
        # Simplify the messages/context and retry
        messages = state.get("messages", [])
        if len(messages) > 3:
            # Keep only recent messages
            simplified_messages = messages[:1] + messages[-2:]
            return {
                "messages": simplified_messages,
                "next_step": "RETRY",
                "recovered": True,
            }

    elif action == "retry_with_delay":
        # Signal that a delay should be applied before retry
        import time
        time.sleep(5)  # Simple delay
        return {
            "next_step": "RETRY",
            "recovered": True,
        }

    elif action == "skip_tool":
        # Mark the problematic tool and continue
        return {
            "skip_tools": state.get("skip_tools", []) + [state.get("failed_tool")],
            "next_step": "CONTINUE",
            "recovered": True,
        }

    elif action == "retry_with_format":
        # Add explicit format instructions
        from langchain_core.messages import HumanMessage
        messages = state.get("messages", [])
        messages.append(
            HumanMessage(content="Please provide your response in a clear, structured format.")
        )
        return {
            "messages": messages,
            "next_step": "RETRY",
            "recovered": True,
        }

    elif action == "simplify":
        # Reduce scope of the research
        plan = state.get("plan", {})
        if plan and "tasks" in plan:
            # Reduce to essential tasks only
            essential_tasks = [t for t in plan["tasks"] if t.get("assigned_agent") in ["researcher", "editor"]]
            plan["tasks"] = essential_tasks[:3]  # Limit to 3 tasks
            return {
                "plan": plan,
                "next_step": "RETRY",
                "recovered": True,
            }

    elif action == "retry_with_backoff":
        # Exponential backoff for rate limits
        import time
        error_count = state.get("error_count", 0)
        delay = min(60, 2 ** error_count)
        time.sleep(delay)
        return {
            "next_step": "RETRY",
            "recovered": True,
        }

    # Default: report the error
    return {
        "next_step": "ERROR_FINAL",
        "recovered": False,
    }


def wrap_node_with_error_handling(node_func):
    """
    Decorator to wrap a node function with error handling.

    Usage:
        @wrap_node_with_error_handling
        def my_node(state):
            # node logic
            return updates
    """
    def wrapper(state: AgentState) -> Dict[str, Any]:
        try:
            return node_func(state)
        except Exception as e:
            logger.error(
                "Node failed with error",
                node=node_func.__name__,
                error=str(e),
            )
            return {
                "last_error": str(e),
                "failed_node": node_func.__name__,
                "next_step": "ERROR_HANDLER",
            }
    return wrapper
