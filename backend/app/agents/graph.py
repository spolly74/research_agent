from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from app.agents.state import AgentState
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.reviewer import reviewer_node
from app.agents.nodes.coder import coder_node
from app.agents.nodes.editor import editor_node
from app.agents.nodes.approval import approval_node
from app.agents.nodes.orchestrator import orchestrator_node
from langgraph.prebuilt import ToolNode
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

# Compile
graph = workflow.compile(checkpointer=MemorySaver())
