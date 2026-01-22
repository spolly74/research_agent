from langchain_core.messages import HumanMessage, SystemMessage
import structlog

from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType
from app.core.execution_tracker import get_execution_tracker, ExecutionPhase
from app.agents.tools.registry import get_tool_registry

logger = structlog.get_logger(__name__)


def researcher_node(state: AgentState):
    """
    The Researcher agent looks up information using tools.

    Gets available tools from the registry dynamically.
    Uses the plan to guide comprehensive research.
    """
    messages = state["messages"]
    session_id = state.get("session_id")
    plan = state.get("plan", {})
    scope_config = state.get("scope_config", {})

    # Get execution tracker
    tracker = get_execution_tracker()

    # Update tracking: Researcher started
    if session_id:
        tracker.update_phase(session_id, ExecutionPhase.RESEARCHING, "Gathering information from sources")
        tracker.set_active_agent(session_id, "researcher", ["browser_search", "visit_page"])

    # Get tools from registry
    registry = get_tool_registry()
    tools = registry.get_tools_for_agent("researcher")

    # Fallback if no tools registered
    if not tools:
        from app.agents.tools.browser import browser_search, visit_page
        tools = [browser_search, visit_page]

    logger.info("Researcher starting", tool_count=len(tools))

    # Initialize LLM with tools - researcher uses Ollama by default
    llm = get_llm(task_type=TaskType.RESEARCHER)
    llm_with_tools = llm.bind_tools(tools)

    # Extract research tasks from plan for guidance
    research_tasks = []
    if plan and "tasks" in plan:
        research_tasks = [
            t["description"] for t in plan["tasks"]
            if t.get("assigned_agent") == "researcher"
        ]

    # Get scope info for research depth
    target_sources = scope_config.get("min_sources", 5) if scope_config else 5
    target_pages = scope_config.get("target_pages", 3) if scope_config else 3

    # Build research guidance from plan
    research_guidance = ""
    if research_tasks:
        research_guidance = f"""
    ## Research Tasks from Plan
    You must gather information for ALL of these research areas:
    {chr(10).join(f'    {i+1}. {task}' for i, task in enumerate(research_tasks))}

    ## Research Requirements
    - Target at least {target_sources} sources total
    - This is for a {target_pages}-page report, so gather SUBSTANTIAL information
    - Perform MULTIPLE searches to cover each research task
    - Don't stop after one search - continue until you have enough material
    """

    # System prompt to guide the researcher
    system_msg = SystemMessage(content=f"""
    You are a Senior Research Agent. Your goal is to find deep, accurate information on the web.
    Use the available tools to search and visit pages.
    Analyze the results and synthesize them.

    {research_guidance}

    CRITICAL INSTRUCTIONS:
    1. RELY ONLY on the information returned by the tools.
    2. DO NOT invent links or "user guides" that do not exist.
    3. If the tool returns no useful information, attempt a different search query.
    4. If you still cannot find info, state "I could not find information on this topic."
    5. Perform MULTIPLE SEARCHES to cover different aspects of the topic.
    6. For each search, also visit the most relevant pages to get detailed information.
    7. Continue researching until you have sufficient material for a comprehensive report.
    """)

    # Update progress
    if session_id:
        tracker.update_agent_progress(session_id, 0.3, "Invoking LLM with research tools")

    # Invoke
    response = llm_with_tools.invoke([system_msg] + messages)

    # Update tracking: Researcher completed
    if session_id:
        result_preview = response.content[:100] if response.content else "No content"
        tracker.complete_agent(session_id, f"Research completed: {result_preview}...")

    logger.info("Researcher completed", content_length=len(response.content) if response.content else 0)

    # Update state
    return {"messages": [response], "research_data": [response.content]}
