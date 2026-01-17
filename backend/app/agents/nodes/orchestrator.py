from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

from app.models.plan import Plan, Task

def orchestrator_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()
    structured_llm = llm.with_structured_output(Plan)

    system_msg = SystemMessage(content="""
    You are the Chief Research Orchestrator.
    Your goal is to break down a user's request into a detailed, step-by-step RESEARCH PLAN.

    1. Analyze the user's request.
    2. Create a list of tasks.
    3. Assign each task to one of the following agents:
       - 'researcher': For finding information, searching the web, or reading pages.
       - 'coder': For writing python scripts, data analysis, or generating charts.
       - 'reviewer': For critiquing research or code.
       - 'editor': For compiling the final answer.

    Ensure the plan is logical and covers all aspects of the request.
    """)

    # If we already have a plan, we might be here to update it (future logic),
    # but for now, we only generate it once at the start.
    if state.get("plan"):
        print("--- Orchestrator: Plan already exists. Skipping generation. ---")
        return {"next_step": "PLAN_EXISTING"}

    print("--- Orchestrator: Generating Research Plan ---")
    plan = structured_llm.invoke([system_msg] + messages)

    # Log the plan for debugging
    print(f"--- Orchestrator: Created Plan with {len(plan.tasks)} tasks. Main Goal: {plan.main_goal} ---")
    for t in plan.tasks:
        print(f"  [{t.id}] {t.status.upper()}: {t.description} ({t.assigned_agent})")

    return {"plan": plan.model_dump(), "next_step": "PLAN_CREATED"}
