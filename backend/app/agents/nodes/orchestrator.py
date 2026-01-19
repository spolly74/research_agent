from langchain_core.messages import SystemMessage
import structlog

from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType, analyze_complexity
from app.core.execution_tracker import get_execution_tracker, ExecutionPhase
from app.models.plan import Plan, Task, ScopeInfo, ResearchParameters
from app.reports.scope_config import detect_scope_from_query, create_scope_config

logger = structlog.get_logger(__name__)


def orchestrator_node(state: AgentState):
    messages = state["messages"]
    session_id = state.get("session_id")

    # Get execution tracker for status updates
    tracker = get_execution_tracker()

    # Update tracking: Orchestrator started
    if session_id:
        tracker.set_active_agent(session_id, "orchestrator")
        tracker.update_phase(session_id, ExecutionPhase.PLANNING, "Analyzing request and creating plan")

    # Analyze complexity of the user's request
    user_message = messages[-1].content if messages else ""
    complexity = analyze_complexity(user_message)

    # Detect scope from user's request
    scope_config = create_scope_config(query=user_message)
    research_params = scope_config.get_research_parameters()

    logger.info(
        "Orchestrator analyzing request",
        complexity=complexity.score,
        scope=scope_config.scope.value,
        target_words=scope_config.parameters.target_word_count
    )

    # Get LLM with task-appropriate routing
    llm = get_llm(
        task_type=TaskType.ORCHESTRATOR,
        prompt=user_message,
        complexity_score=complexity.score
    )
    structured_llm = llm.with_structured_output(Plan)

    # Build scope-aware system prompt
    scope_guidance = _get_scope_guidance(scope_config)

    system_msg = SystemMessage(content=f"""
    You are the Chief Research Orchestrator.
    Your goal is to break down a user's request into a detailed, step-by-step RESEARCH PLAN.

    1. Analyze the user's request.
    2. Create a list of tasks.
    3. Assign each task to one of the following agents:
       - 'researcher': For finding information, searching the web, or reading pages.
       - 'coder': For writing python scripts, data analysis, or generating charts.
       - 'reviewer': For critiquing research or code.
       - 'editor': For compiling the final answer.

    {scope_guidance}

    Ensure the plan is logical and covers all aspects of the request.
    """)

    # If we already have a plan, we might be here to update it (future logic),
    # but for now, we only generate it once at the start.
    if state.get("plan"):
        logger.info("Plan already exists, skipping generation")
        return {"next_step": "PLAN_EXISTING"}

    logger.info("Generating research plan")
    plan = structured_llm.invoke([system_msg] + messages)

    # Add scope information to the plan
    plan.scope = ScopeInfo(
        scope=scope_config.scope.value,
        target_pages=scope_config.parameters.target_pages,
        target_word_count=scope_config.parameters.target_word_count,
        research_params=ResearchParameters(
            min_sources=research_params["min_sources"],
            max_sources=research_params["max_sources"],
            depth=research_params["depth"],
            focus=research_params["focus"]
        )
    )

    # Log the plan for debugging
    logger.info(
        "Plan created",
        task_count=len(plan.tasks),
        main_goal=plan.main_goal,
        scope=plan.scope.scope
    )
    for t in plan.tasks:
        logger.debug(
            "Plan task",
            task_id=t.id,
            status=t.status,
            description=t.description,
            agent=t.assigned_agent
        )

    # Update tracking: Plan created
    plan_dict = plan.model_dump()
    if session_id:
        tracker.set_plan(session_id, plan_dict)
        tracker.complete_agent(session_id, f"Plan created with {len(plan.tasks)} tasks")
        tracker.update_agent_progress(session_id, 1.0, "Planning complete")

    return {
        "plan": plan_dict,
        "next_step": "PLAN_CREATED",
        "scope_config": scope_config.to_dict()
    }


def _get_scope_guidance(scope_config) -> str:
    """Generate scope-specific guidance for the orchestrator."""
    params = scope_config.parameters

    if scope_config.scope.value == "brief":
        return f"""
    ## Report Scope: BRIEF (1-2 pages)
    - This is a brief report request. Plan for a quick, focused research effort.
    - Target {params.min_sources}-{params.max_sources} sources maximum.
    - Focus on gathering key facts only - no deep dives.
    - The editor should produce a concise summary.
    - Skip detailed methodology or extensive background research.
    """

    elif scope_config.scope.value == "comprehensive":
        return f"""
    ## Report Scope: COMPREHENSIVE (10-15 pages)
    - This is a comprehensive report request. Plan for thorough, detailed research.
    - Target {params.min_sources}-{params.max_sources} sources.
    - Include multiple research tasks to cover different aspects.
    - Include tasks for methodology and background research.
    - The editor should produce a detailed, well-structured report.
    - Consider adding a reviewer task to ensure quality.
    """

    else:  # standard or custom
        return f"""
    ## Report Scope: STANDARD (3-5 pages)
    - This is a standard report request. Plan for balanced research.
    - Target {params.min_sources}-{params.max_sources} sources.
    - Cover the main aspects without excessive detail.
    - The editor should produce a balanced, informative report.
    """
