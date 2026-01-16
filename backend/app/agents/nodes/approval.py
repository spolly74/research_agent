from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def approval_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    system_msg = SystemMessage(content="""
    You are the Approval Agent. Check if the deliverables meet the user's goal.
    Return 'APPROVED' if good, or 'REJECTED' if more work is needed.
    """)

    response = llm.invoke([system_msg] + messages)
    # Simple heuristic processing of the response
    status = "APPROVED" if "APPROVED" in response.content else "REJECTED"

    return {"next_step": status}
