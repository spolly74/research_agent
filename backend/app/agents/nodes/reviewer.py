from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm_manager import get_llm, TaskType

def reviewer_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm(task_type=TaskType.REVIEWER)

    system_msg = SystemMessage(content="""
    You are a Review Agent. Critique the research findings.
    Check for completeness, accuracy, and relevance.
    If the research is lacking, provide specific feedback.
    """)

    response = llm.invoke([system_msg] + messages)
    return {"messages": [response], "review_feedback": response.content}
