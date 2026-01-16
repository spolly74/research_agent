from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def editor_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    system_msg = SystemMessage(content="""
    You are an Editor Agent. Ensure the final output is consistent, well-formatted, and professional.
    Synthesize the research, code, and reviews into a final report.
    """)

    response = llm.invoke([system_msg] + messages)
    return {"messages": [response], "final_report": response.content}
