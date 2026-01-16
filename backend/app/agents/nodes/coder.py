from langchain_core.messages import SystemMessage
from app.agents.state import AgentState
from app.core.llm import get_llm

def coder_node(state: AgentState):
    messages = state["messages"]
    llm = get_llm()

    system_msg = SystemMessage(content="""
    You are a Coder Agent. Your job is to write python tools or scripts if needed.
    For now, analyze if any custom code is needed to solve the user's request.
    """)

    response = llm.invoke([system_msg] + messages)
    return {"messages": [response], "code_output": response.content}
