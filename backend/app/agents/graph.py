from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import structlog

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


def get_researcher_tools():
    """Get tools available to the researcher agent from the registry."""
    registry = get_tool_registry()
    return registry.get_tools_for_agent("researcher")


# Get tools from registry (will be populated on startup)
# Fallback to browser tools if registry not yet initialized
try:
    tools = get_researcher_tools()
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
        print("--- Orchestrator: Routing to Researcher ---")
        return "researcher"
    print("--- Orchestrator: Routing to Editor ---")
    return "editor"

workflow.add_conditional_edges("orchestrator", route_orchestrator)

# Add edges
def should_continue(state):
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        print("--- Graph: Routing to Tools ---")
        return "tools"
    print("--- Graph: Routing to Reviewer ---")
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
