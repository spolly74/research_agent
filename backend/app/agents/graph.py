from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog
import os
from typing import Optional

from app.agents.state import AgentState
from app.core.checkpointer import get_database_checkpointer, DatabaseCheckpointer

logger = structlog.get_logger(__name__)
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.reviewer import reviewer_node
from app.agents.nodes.coder import coder_node
from app.agents.nodes.editor import editor_node
from app.agents.nodes.approval import approval_node
from app.agents.nodes.orchestrator import orchestrator_node
from langgraph.prebuilt import ToolNode
from app.agents.tools.registry import get_tool_registry


# Track the graph version for dynamic tool updates
_graph_version = 0
_compiled_graph = None


def get_researcher_tools():
    """Get tools available to the researcher agent from the registry."""
    registry = get_tool_registry()
    return registry.get_tools_for_agent("researcher")


def get_all_agent_tools():
    """Get all tools that should be available in the graph."""
    registry = get_tool_registry()
    # Get tools for all agents that use the tool node
    researcher_tools = registry.get_tools_for_agent("researcher")
    coder_tools = registry.get_tools_for_agent("coder")

    # Combine and deduplicate by name
    seen_names = set()
    all_tools = []
    for tool in researcher_tools + coder_tools:
        if tool.name not in seen_names:
            all_tools.append(tool)
            seen_names.add(tool.name)

    return all_tools


def _create_workflow():
    """Create a fresh workflow graph with current tools."""
    # Get tools from registry (will be populated on startup)
    # Fallback to browser tools if registry not yet initialized
    try:
        tools = get_all_agent_tools()
        if not tools:
            from app.agents.tools.browser import browser_search, visit_page
            tools = [browser_search, visit_page]
    except Exception as e:
        logger.warning("Error loading tools from registry, using fallback", error=str(e))
        from app.agents.tools.browser import browser_search, visit_page
        tools = [browser_search, visit_page]

    logger.info("Creating workflow with tools", tool_count=len(tools), tools=[t.name for t in tools])

    # Define the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("editor", editor_node)
    workflow.add_node("approval", approval_node)
    workflow.add_node("tools", ToolNode(tools))

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Conditional Routing from Orchestrator
    def route_orchestrator(state):
        step = state.get("next_step", "ANSWER")
        if step == "RESEARCH":
            logger.debug("Orchestrator routing to researcher", next_step=step)
            return "researcher"
        logger.debug("Orchestrator routing to editor", next_step=step)
        return "editor"

    workflow.add_conditional_edges("orchestrator", route_orchestrator)

    # Add edges
    def should_continue(state):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            logger.debug("Graph routing to tools", tool_call_count=len(last_message.tool_calls))
            return "tools"
        logger.debug("Graph routing to reviewer")
        return "reviewer"

    workflow.add_conditional_edges("researcher", should_continue)
    workflow.add_edge("tools", "researcher")
    workflow.add_edge("reviewer", "coder")
    workflow.add_edge("coder", "editor")
    workflow.add_edge("editor", "approval")
    workflow.add_edge("approval", END)

    return workflow


# Get tools from registry (will be populated on startup)
# Fallback to browser tools if registry not yet initialized
try:
    tools = get_all_agent_tools()
    if not tools:
        from app.agents.tools.browser import browser_search, visit_page
        tools = [browser_search, visit_page]
except:
    from app.agents.tools.browser import browser_search, visit_page
    tools = [browser_search, visit_page]

# Define the graph
workflow = StateGraph(AgentState)

# Add nodes
# Add nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("coder", coder_node)
workflow.add_node("editor", editor_node)
workflow.add_node("approval", approval_node)
workflow.add_node("tools", ToolNode(tools))

# Set entry point
workflow.set_entry_point("orchestrator")

# Conditional Routing from Orchestrator
def route_orchestrator(state):
    step = state.get("next_step", "ANSWER")
    if step == "RESEARCH":
        logger.debug("Orchestrator routing to researcher", next_step=step)
        return "researcher"
    logger.debug("Orchestrator routing to editor", next_step=step)
    return "editor"

workflow.add_conditional_edges("orchestrator", route_orchestrator)

# Add edges
def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        logger.debug("Graph routing to tools", tool_call_count=len(last_message.tool_calls))
        return "tools"
    logger.debug("Graph routing to reviewer")
    return "reviewer"

workflow.add_conditional_edges("researcher", should_continue)
workflow.add_edge("tools", "researcher")
# workflow.add_edge("researcher", "reviewer") # Replaced by conditional
workflow.add_edge("reviewer", "coder") # Optional step
workflow.add_edge("coder", "editor")
workflow.add_edge("editor", "approval")
workflow.add_edge("approval", END)

# Configure checkpointer
# Use environment variable to choose between memory (dev) and database (prod)
import os
USE_DB_CHECKPOINTER = os.environ.get("USE_DB_CHECKPOINTER", "true").lower() == "true"

if USE_DB_CHECKPOINTER:
    try:
        checkpointer = get_database_checkpointer()
        logger.info("Using database checkpointer for state persistence")
    except Exception as e:
        logger.warning("Failed to initialize database checkpointer, falling back to memory", error=str(e))
        checkpointer = MemorySaver()
else:
    checkpointer = MemorySaver()
    logger.info("Using memory checkpointer (state will not persist)")

# Compile
graph = workflow.compile(checkpointer=checkpointer)


def get_session_state(thread_id: str) -> dict:
    """
    Retrieve the current state for a session.

    Args:
        thread_id: The session thread ID

    Returns:
        The current state dict or empty dict if not found
    """
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = graph.get_state(config)
        if state and state.values:
            return state.values
        return {}
    except Exception as e:
        logger.error("Error getting session state", error=str(e), thread_id=thread_id)
        return {}


def can_resume_session(thread_id: str) -> bool:
    """
    Check if a session can be resumed.

    Args:
        thread_id: The session thread ID

    Returns:
        True if the session has state that can be resumed
    """
    state = get_session_state(thread_id)
    return bool(state and state.get("messages"))


def refresh_graph():
    """
    Refresh the graph with current tools from the registry.

    Call this after dynamically creating new tools to ensure the graph
    has access to them.

    Returns:
        The new compiled graph
    """
    global _graph_version, _compiled_graph, graph

    _graph_version += 1
    logger.info("Refreshing graph with updated tools", version=_graph_version)

    # Create new workflow with current tools
    new_workflow = _create_workflow()

    # Configure checkpointer
    if USE_DB_CHECKPOINTER:
        try:
            new_checkpointer = get_database_checkpointer()
        except Exception as e:
            logger.warning("Failed to get database checkpointer", error=str(e))
            new_checkpointer = MemorySaver()
    else:
        new_checkpointer = MemorySaver()

    # Compile new graph
    _compiled_graph = new_workflow.compile(checkpointer=new_checkpointer)
    graph = _compiled_graph

    logger.info("Graph refreshed successfully", version=_graph_version)
    return graph


def get_current_graph():
    """
    Get the current compiled graph.

    Returns:
        The current compiled graph instance
    """
    global graph
    return graph


def get_graph_info() -> dict:
    """
    Get information about the current graph configuration.

    Returns:
        Dict with graph info including tool count and version
    """
    global _graph_version

    try:
        current_tools = get_all_agent_tools()
        tool_names = [t.name for t in current_tools]
    except:
        tool_names = []

    return {
        "version": _graph_version,
        "tool_count": len(tool_names),
        "tools": tool_names,
        "checkpointer_type": "database" if USE_DB_CHECKPOINTER else "memory",
    }
