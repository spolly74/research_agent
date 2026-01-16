from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def orchestrator_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    system_msg = SystemMessage(content="""
    You are the Orchestrator. Your job is to decide the NEXT STEP.
    Analyze the user's latest request.

    - If the user is asking a general knowledge question (e.g. "Hi", "Who are you?", "What is the capital of France?"), return 'ANSWER'.
    - If the user is asking for specific, obscure, or real-time information that requires searching the web (e.g. "Stock price of Apple", "Latest news on AI"), return 'RESEARCH'.

    Output ONLY one word: 'ANSWER' or 'RESEARCH'.
    """)

    response = llm.invoke([system_msg] + messages)
    decision = response.content.strip().upper()

    # Default fallback
    if "RESEARCH" in decision:
        decision = "RESEARCH"
    else:
        decision = "ANSWER"

    print(f"--- Orchestrator: Routing to {decision} ---")
    return {"next_step": decision}
