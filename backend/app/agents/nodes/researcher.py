from langchain_core.messages import HumanMessage, SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm
from app.agents.tools.browser import browser_search, visit_page

def researcher_node(state: AgentState):
    """
    The Researcher agent looks up information using tools.
    """
    messages = state["messages"]

    # Initialize LLM with tools
    llm = get_llm()
    tools = [browser_search, visit_page]
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
    # Invoke
    print("--- Researcher Node: invoking LLM ---")
    response = llm_with_tools.invoke([system_msg] + messages)
    print(f"--- Researcher Node: received response: {response.content} ---")
    print(f"--- Researcher Node: tool calls: {response.tool_calls} ---")

    # Update state
    return {"messages": [response], "research_data": [response.content]}
