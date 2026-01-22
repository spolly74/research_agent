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

    ## Task Creation Guidelines
    1. Analyze the user's request carefully.
    2. Create MULTIPLE research tasks - one task per distinct aspect of the topic.
    3. Each research task should have a specific, actionable description.
    4. Order tasks logically (background first, then analysis, then conclusions).

    ## Available Agents
    Assign each task to one of these agents:
    - 'researcher': For finding information, searching the web, reading pages. Use for EACH distinct research question.
    - 'coder': For writing python scripts, data analysis, generating charts.
    - 'reviewer': For critiquing research or code, ensuring quality.
    - 'editor': For compiling the final answer into a polished report.

    ## CRITICAL: Task Descriptions
    Each research task description should be a SPECIFIC search query or investigation, such as:
    - "Research the history and origins of [topic]"
    - "Find data and statistics about [specific aspect]"
    - "Investigate arguments for and against [position]"
    - "Search for expert opinions and analysis on [topic]"
    - "Find case studies or real-world examples of [topic]"

    {scope_guidance}

    ## Task Requirements
    - Create enough research tasks to gather sufficient material for the requested report length.
    - Each task should focus on ONE specific aspect to ensure thorough coverage.
    - Include an 'editor' task at the end to compile all research into the final report.
    - The editor task description should include the target word count.
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
    target_pages = params.target_pages
    target_words = params.target_word_count

    # Calculate recommended research tasks based on page count
    # More pages = more research tasks to gather sufficient material
    if target_pages <= 2:
        min_research_tasks = 2
        max_research_tasks = 3
        depth_desc = "quick, focused"
    elif target_pages <= 5:
        min_research_tasks = 3
        max_research_tasks = 5
        depth_desc = "balanced, thorough"
    elif target_pages <= 10:
        min_research_tasks = 5
        max_research_tasks = 8
        depth_desc = "detailed, comprehensive"
    else:
        min_research_tasks = 8
        max_research_tasks = 12
        depth_desc = "exhaustive, academic-level"

    if scope_config.scope.value == "brief":
        return f"""
    ## Report Scope: BRIEF ({target_pages} pages, ~{target_words} words)
    - This is a brief report request. Plan for a quick, focused research effort.
    - Create {min_research_tasks}-{max_research_tasks} focused research tasks.
    - Target {params.min_sources}-{params.max_sources} sources total.
    - Focus on gathering key facts only - no deep dives.
    - The editor should produce a concise summary of ~{target_words} words.
    """

    elif scope_config.scope.value == "comprehensive":
        return f"""
    ## Report Scope: COMPREHENSIVE ({target_pages} pages, ~{target_words} words)
    - This is a comprehensive report request. Plan for {depth_desc} research.
    - Create {min_research_tasks}-{max_research_tasks} research tasks covering different aspects.
    - Target {params.min_sources}-{params.max_sources} sources total.
    - Each research task should explore a different facet of the topic.
    - Include tasks for: background/context, main analysis, supporting evidence, counterarguments, case studies.
    - The editor MUST produce a detailed report of ~{target_words} words ({target_pages} pages).
    - Consider adding a reviewer task to ensure quality and depth.
    """

    else:  # standard or custom
        return f"""
    ## Report Scope: {target_pages}-PAGE REPORT (~{target_words} words)
    - The user has requested a {target_pages}-page report. Plan accordingly.
    - Create {min_research_tasks}-{max_research_tasks} research tasks to gather sufficient material.
    - Target {params.min_sources}-{params.max_sources} sources total.
    - Each research task should cover a distinct aspect of the topic:
      * Background and context
      * Core analysis / main arguments
      * Supporting evidence and data
      * Implications or conclusions
    - The editor MUST produce a report of approximately {target_words} words ({target_pages} pages).
    - This requires {depth_desc} research - not just surface-level information.
    """
