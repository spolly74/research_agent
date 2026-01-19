from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType
from app.agents.tools.registry import get_tool_registry


def researcher_node(state: AgentState):
    """
    The Researcher agent looks up information using tools.

    Gets available tools from the registry dynamically.
    """
    messages = state["messages"]

    # Get tools from registry
    registry = get_tool_registry()
    tools = registry.get_tools_for_agent("researcher")

    # Fallback if no tools registered
    if not tools:
        from app.agents.tools.browser import browser_search, visit_page
        tools = [browser_search, visit_page]

    # Initialize LLM with tools - researcher uses Ollama by default
    llm = get_llm(task_type=TaskType.RESEARCHER)
    llm_with_tools = llm.bind_tools(tools)

    # System prompt to guide the researcher
    system_msg = SystemMessage(content="""
    You are a Senior Research Agent. Your goal is to find deep, accurate information on the web.
    Use the available tools to search and visit pages.
    Analyze the results and synthesize them.

    CRITICAL INSTRUCTIONS:
    1. RELY ONLY on the information returned by the tools.
    2. DO NOT invent links or "user guides" that do not exist.
    3. If the tool returns no useful information, attempt a different search query.
    4. If you still cannot find info, state "I could not find information on this topic."
    """)

    # Invoke
    response = llm_with_tools.invoke([system_msg] + messages)

    # Update state
    return {"messages": [response], "research_data": [response.content]}
